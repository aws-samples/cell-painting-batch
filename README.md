# Cell Painting Batch(CPB)


The Cell Painting Batch (CPB) is an Amazon Web Services (AWS) solution tailored for large-scale image processing tasks using cell profiler pipelines on AWS. This solution is built upon the Cell Profiler image from Broad Institute, tailored for large-scale image processing tasks using scalable and distributed Amazon Web Services (AWS) infrastructure. The solution is constructed using the Cloud Development Kit (CDK) in the Python language and subsequently deployed via AWS CloudFormation Stacks.


 
## Table of Contents

- [Introduction](#introduction)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment](#deploy)
- [Operation](#operate)
- [Monitoring](#monitor)
- [Cleanup](#destroy)
- [Contributing](#contributing)
- [License](#license)



# Introduction

Embracing a high degree of automation and cloud-centric solutions, CPB aims to redefine the efficiency of cell painting tasks on AWS. By building on top of the Cell Profiler image from the Broad Institute, the solution provides researchers with a platform that accelerates large-scale image processing endeavors. With a design focused on ease of use, scientists can tap into a ready-made infrastructure capable of handling massive data sets and complex processing tasks.



# Architecture 

The core of CPB is a well-orchestrated set of Amazon Web Services (AWS) services, each playing a pivotal role in the solution's efficiency. Central to this system, microscope images are uploaded to an Amazon Simple Storage Service (S3) bucket. When researchers upload their images, they initiate the workflow by sending an Amazon Simple Queue Service (SQS) message. Upon its receipt, an AWS Lambda function springs into action, subsequently triggering an AWS Batch job. AWS Batch takes charge of the computation, dynamically allocating Amazon Elastic Compute Cloud (EC2) instances tailored to the job's demands. It retrieves the designated container from Amazon Elastic Container Registry (ECR), which then processes the images using the Cell Profiler pipeline based on specifications in the SQS message. To optimize data performance, Amazon FSx for Lustre is implemented, making data from the S3 bucket rapidly accessible to containers. Once processing concludes, the results are promptly saved back to the S3 bucket, ready for researchers' further analysis.


The below diagram outlines the architecture of the cell painting batch solution on AWS.
 
![Architecture Diagram](./assets/logical-architecture.png?raw=true "Cell Painting Batch Architecture")


### Components:

1. **Virtual Private Cloud (VPC)**:- An isolated segment of the AWS Cloud where resources are launched within a software defined virtual network.
1. **Simple Storage Service (S3)**:- An object storage service that offers scalable storage. Used here for dropping microscope images and storing processed results.
1. **Simple Queue Service (SQS)**:- A managed message queuing service. Researchers submit messages about desired image processing, serving as the processing trigger.
1. **Lambda**:- A serverless compute service that runs code in response to events. In this setup, it's triggered by SQS to initiate an AWS Batch job.
1. **AWS Batch**:- A service that manages batch computing workloads, provisioning resources dynamically based on job requirements.
1. **Elastic Container Registry (ECR)**:- A fully-managed Docker container registry. Houses the Cell Profiler container image for use by AWS Batch.
1. **Elastic Compute Cloud (EC2)**:- Provides scalable compute capacity in the cloud. Used by AWS Batch to provision instances for processing.


9. **Amazon FSx for Lustre**:- A high-performance file system optimized for fast processing workloads. Integrated with the S3 bucket, it ensures that data is available to containers for enhanced performance.

These AWS services, when combined, provide a seamless, scalable, and efficient architecture tailored for extensive cell painting image analysis.


# Workflow / Process Flow


The Cell Painting Batch  workflow has been designed to simplify and automate the large-scale processing of cell painting images. Below is the step-by-step process flow for a typical run:

1. **Image Acquisition:** - Researchers obtain images from microscopes or other sources.
   
2. **Image Storage:** - These images are then uploaded to a designated AWS S3 bucket, acting as an image repository.
   
3. **Job Initiation:** - Once images are stored, researchers craft an SQS message with details about the image location and the desired Cell Profiler pipeline. This SQS message is sent to the AWS SQS service, essentially acting as a request for image processing.

4. **Lambda Trigger:** - On the receipt of an SQS message, a Lambda function is automatically triggered. This function's primary role is to initiate the AWS Batch job for the particular image processing request.

5. **AWS Batch Execution:** - AWS Batch comes into action, evaluating the requirements of the job. Depending on the nature of the task, AWS Batch dynamically provisions the necessary EC2 instances, ensuring optimal resource allocation.

6. **Container Execution:** - The specified container image, stored in AWS ECR, is fetched. Within AWS Batch, this container executes, running the defined Cell Profiler pipeline on the image specified in the SQS message. Amazon FSx for Lustre integrated with S3 bucket ensures that data is available to containers with enhanced performance.

7. **Cell Profiler Image Processing:** - The Cell Profiler software, encapsulated in the container, processes the image through a series of defined steps based on the pipeline definition. This may involve segmenting the image, extracting features, and various other image processing tasks.

8. **Results Storage:** - Once the Cell Profiler completes its tasks, the processed results (which could be processed images, data tables, or any other output) are saved. These results are then stored back to an AWS S3 bucket on a location specified in the SQS message.

9. **Result Retrieval and Analysis:** - Researchers can then access this S3 bucket, downloading and analyzing the results for their scientific studies.

The entire workflow is automated, ensuring that once an image is uploaded and an SQS message is sent, the system handles everything, from image processing to result storage. This provides researchers with a hands-free, efficient, and scalable solution for their large-scale image processing needs.



# Prerequisites

Before initiating deployment:

- An AWS account with necessary resource creation permissions.
- Set up a AWS Cloud9 instance, following the guide [here](https://www.hpcworkshops.com/03-parallel-cluster-cli/03-start_cloud9.html). 
- AWS CDK: Familiarize yourself with [AWS CDK basics](https://docs.aws.amazon.com/cdk/v2/guide/home.html).

**In the Cloud9 IDE:**

Resize the root volume:

```bash
curl 'https://static.us-east-1.prod.workshops.aws/public/e74a005d-e7a0-4390-aaa8-8281446a567a/static/resources/resize.sh' --output resize.sh
chmod +x resize.sh
./resize.sh 50
```

Install Docker:

```bash
sudo yum install docker
```

The rest of the Workshop dependencies are pre-installed by default in Cloud9. To confirm, run: 

```bash
python --version #Confirm Python 3.6 or later
pip --version #Python package installer
node --version #Node.js
npm --version #Node Package Manager
aws --version #AWS Command Line Interface (CLI)
```

Install any missing packages before continuing. 

# Deployment

The following steps guide you through initializing and deploying the infrastructure:

## 1.Initial setup 
Open Cloud9 environment and run the commands below to initialize CDK pipeline for deployment.
 
```bash
# Bootstrap CDK 
python -m pip install aws-cdk-lib
npm install -g aws-cdk
npm install -g aws-cdk --force
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
cdk bootstrap aws://$ACCOUNT_ID/us-east-1
cdk --version 
```

## 2. Create Infrastructure 

Create a virtual environment, install the necessary Python packages, and deply infrastruture using CDK.

Clone the git repo (skip if done previously)

```bash
git clone https://github.com/aws-samples/cell-painting-batch.git
```

Create and activate a Python virtual environment

```bash
python3 -m venv .venv-cpb
source .venv-cpb/bin/activate
```

Install Python packages from 'requirements.txt'

```bash
pip install -r requirements.txt
```

*(Optional)* The file `constants.py` contains CDK settings, including Region and Batch Compute Environment parameters. Review and edit the contents of this file as needed before synthesizing the CDK templates:

```bash
vim constants.py
```

Synthesize CDK

```bash
cdk synth
```

Deploy network infrastructure using CDK. This will create a new VPC and security group. Deploy:

```bash
cdk deploy network-cpb
```

Deploy Batch infrastructure using CDK. This step creates the Batch Compute Environment and Queue, an FSx for Lustre Filesystem, and the required IAM roles. This step will take ~20 minutes.

```bash
cdk deploy batch-cpb
```

***Optional:*** Run these commands if you need cloud formation templates:

```bash
cdk synth network-cpb > files/network.yaml
cdk synth batch-cpb > files/batch.yaml
```

## 3. After deployment:

Monitor the progress using the AWS CloudFormation service.

![AWS CloudFormation Stack Status](./assets/batch-cpb-cfn-status.png?raw=true "AWS CloudFormation Stack Status")


- Inspect the created resources such as AWS Batch, SQS, Lambda, Amazon S3, Amazon EC2, Elastic Container Registry (ECR), and Amazon FSx for Lustre.

# Operation

After deploying the infrastructure, you can submit jobs through SQS.

### Upload Example pipelines & data

Execute the command below to upload sample data and pipelines from the GitHub repository to the designated S3 bucket.

Retrieve the AWS_BUCKET environment variable using AWS CLI

```bash
AWS_BUCKET=$(aws cloudformation describe-stacks --stack-name batch-cpb --query "Stacks[0].Outputs[?ExportName=='BucketName'].OutputValue" --output text)
```

Clone CellProfiler examples git repo for examples data and pipelines

```bash
git clone https://github.com/CellProfiler/examples.git 
```

Copy the contents to the S3 bucket using the AWS CLI

```bash
aws s3 cp examples "s3://$AWS_BUCKET/examples/" --recursive
```

Remove the cloned repo

```bash
rm -rf examples/
```

### `Job Submission`
Jobs may be submitted either via the AWS Console or using the command line:

#### Option 1 - Via Console: 
Navigate to SQS within the AWS console and input a sample message:

- Submit Single Job 
```json
{
  "pipeline": "examples/ExampleVitraImages/ExampleVitra.cppipe", 
  "input": "examples/ExampleVitraImages/images/",
  "output": "examples/ExampleVitraImages/output0/"
} 
```

- Submit Multiple Jobs 
```json
[
{
  "pipeline": "examples/ExampleVitraImages/ExampleVitra.cppipe", 
  "input": "examples/ExampleVitraImages/images/",
  "output": "examples/ExampleVitraImages/output1/"
},
{
  "pipeline": "examples/ExampleVitraImages/ExampleVitra.cppipe", 
  "input": "examples/ExampleVitraImages/images/",
  "output": "examples/ExampleVitraImages/output2/"
}

]
```

- Submit Multiple Jobs with custom memory and CPU
```json
[
{
  "pipeline": "examples/ExampleVitraImages/ExampleVitra.cppipe", 
  "input": "examples/ExampleVitraImages/images/",
  "output": "examples/ExampleVitraImages/output3/",
  "job_memory":"8192",
  "job_vcpu":"12"  
},
{
  "pipeline": "examples/ExampleVitraImages/ExampleVitra.cppipe", 
  "input": "examples/ExampleVitraImages/images/",
  "output": "examples/ExampleVitraImages/output4/",
  "job_memory":"8192",
  "job_vcpu":"8"  
}

]
```

You can also pass custom "job_definition" arn and  "job_queue" arn as part of the SQS message. 


#### Option 2 - Submit Job using Command line:

Execute the following commands either in Cloud9 or in your terminal to process the messages:



```cli

# Retrieve the SQS_URL using AWS CLI
SQS_URL=$(aws cloudformation describe-stacks --stack-name batch-cpb --query "Stacks[0].Outputs[?ExportName=='SQSQueueURL'].OutputValue" --output text)


aws sqs send-message \
  --queue-url $SQS_URL \
  --message-body '{"pipeline":"examples/ExampleVitraImages/ExampleVitra.cppipe", "input":"examples/ExampleVitraImages/images/", "output":"examples/ExampleVitraImages/output5"}'


```


# Monitoring

Logs related to the deployed resources can be found in AWS CloudWatch. To inspect the logs for specific resources, use the AWS Console. Ensure you've granted the necessary permissions to view these CloudWatch logs.

* To monitor Batch Job progress, open it and navigate to CloudWatch logs.
* To examine the outcomes, go to the designated output folder in the S3 bucket, as specified in the SQS message.


 
# Cleanup

To avoid incurring extra AWS charges, make sure to delete all deployed resources after you're done:


 
```bash
 
# Delete Batch stack
cdk destroy batch-cpb 

# Delete Network stack
cdk destroy network-cpb

```



# Contributing

We welcome and appreciate all contributions! For details on the contribution process, please refer to the Contributing Guide. If you'd like to submit a pull request, view [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for additional information.

 

# License

This software library is under the MIT-0 License. For more details, consult the LICENSE file.



# Reference 

The following resources were used to build this solution:

1. [Cell Profiler](https://github.com/CellProfiler/)
2. [Cell profiler examples](https://github.com/CellProfiler/examples)


 
# Disclaimer

This solution was constructed using the [open source version of Cell Profiler](https://github.com/CellProfiler/examples/blob/master/LICENSE). Cell Profiler operates under the BSD 3-Clause License or subsequent versions. By utilizing this, you acknowledge and consent to fully adhere to all terms and conditions stipulated by the BSD 3-Clause License, including but not restricted to, attribution requirements.
