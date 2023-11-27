# Import necessary AWS CDK modules and other dependencies
from aws_cdk import (
    aws_sqs as sqs,
    Stack,  
    Duration,
    CfnOutput,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_batch_alpha as batch,
    aws_lambda_event_sources as lambda_event_source,
    aws_ecr_assets as ecra,
    aws_fsx as fsx,
    aws_ecs as ecs,
    
  
)
from constructs import Construct
import aws_cdk as core

# The BatchStack class is where we define our AWS Batch environment, including associated resources such as an S3 bucket, an SQS queue, and a Lambda function.

class BatchStack(Stack):

    

    # def __init__(self, scope: Construct, construct_id: str, config, network_stack,**kwargs) -> None:
    def __init__(self, scope: Construct, construct_id: str, config, network_stack,  **kwargs) -> None:
        super().__init__(scope, construct_id,        **kwargs)


        # Prefix for all resource names
        resource_prefix = f"{config['NAME_PREFIX']}-ba"

        # Assign Parameters from config to use in the stack
        AWS_REGION  = config["AWS_REGION"]
        REMOVAL_POLICY = config["REMOVAL_POLICY"]
        AUTO_DELETE_OBJECTS = config["AUTO_DELETE_OBJECTS"]
        COMPUTE_MIN_CPU  = config["COMPUTE_MIN_CPU"]
        COMPUTE_MAX_CPU  = config["COMPUTE_MAX_CPU"]
        COMPUTE_BID_PERCENT  = config["COMPUTE_BID_PERCENT"]
        INSTANCE_CLASS = config["INSTANCE_CLASS"]
        EBS_VOL_SIZE  = config["EBS_VOL_SIZE"]
        JOB_CPU  = config["JOB_CPU"]
        JOB_MEMORY  = config["JOB_MEMORY"]
        JOB_ATTEMPTS  = config["JOB_ATTEMPTS"]
        JOB_TIMEOUT  = config["JOB_TIMEOUT"]
        SQS_MESSAGE_VISIBILITY  = config["SQS_MESSAGE_VISIBILITY"]
        REQUIREMENTS_FILE  = config["REQUIREMENTS_FILE"]
        # Get the current account number  
        current_account = core.Aws.ACCOUNT_ID
 

        # Log group name
        LOG_GROUP_NAME = f"{config['NAME_PREFIX']}-nw-log"
        APP_NAME = f"{resource_prefix}-app"


        # Create Dead Letter Queue
        queue_dead = sqs.Queue(
            self, f"{resource_prefix}-dead-letter",
            retention_period=Duration.days(12),   
            enforce_ssl=True        
        )
 

        # Create Main Queue with dead letter queue configured
        self.queue = sqs.Queue(
            self, f"{resource_prefix}-queue",
            delivery_delay=Duration.seconds(0),
            max_message_size_bytes=262144,
            retention_period=Duration.days(4),
            receive_message_wait_time=Duration.seconds(0),
            visibility_timeout=Duration.seconds(SQS_MESSAGE_VISIBILITY),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=10,
                queue=queue_dead
            ),
            enforce_ssl=True
        )
        self.queue.node.add_dependency(queue_dead)

        # Output the SQS Queue URL
        sqs_output = CfnOutput(self, "SQSQueueURL",
            value=self.queue.queue_url,
            description="The URL of the SQS Queue",
            export_name="SQSQueueURL"
        )


        # Create a unique bucket name using UUID
        AWS_BUCKET = f"{resource_prefix}-data-cp-{current_account}-{AWS_REGION}" #+ str(uuid.uuid4())


        s3_bucket = s3.Bucket(self, 
            f"{resource_prefix}-data",
            bucket_name=AWS_BUCKET,
            removal_policy=REMOVAL_POLICY, # Remove bucket on `cdk destroy`
            auto_delete_objects= AUTO_DELETE_OBJECTS,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True


        )

        # Output the bucket name
        bucket_output = CfnOutput(self, "BucketName",
            value=s3_bucket.bucket_name,
            description="The name of the S3 bucket",
            export_name="BucketName"
        )

  
    
        # Creating IAM Role for Batch Instance
        batch_instance_role = iam.Role(
            self,
            f"{resource_prefix}-batch-instance-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ec2.amazonaws.com"),
                iam.ServicePrincipal("ecs.amazonaws.com"),
                iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"),
            ],
        )
        

        # Granting read/write permissions to S3 bucket for the batch instance role
        s3_bucket.grant_read_write(batch_instance_role)
    
        # Creating Batch Instance Profile
        batch_instance_profile = iam.CfnInstanceProfile(
            self, f"{resource_prefix}-batch-instance-profile", roles=[batch_instance_role.role_name]
        )
    
        # Docker Image
    
        # Specify the directory containing Dockerfile for the AWS Batch job
        docker_base_dir = "docker"
    
        # Creating Docker Image Asset
        docker_image_asset = ecra.DockerImageAsset(
            self,
            f"{resource_prefix}-batch-instance-image-asset",
            directory=docker_base_dir,
            follow_symlinks=core.SymlinkFollowMode.ALWAYS,
        )
    
        # Using the Docker Image Asset for the Container Image
        docker_container_image = ecs.ContainerImage.from_docker_image_asset(
            docker_image_asset
        )
            
        # Output the ECR Repository URL
        CfnOutput(self, "ECRRepositoryURL",
            value=docker_image_asset.image_uri,
            description="The URL of the ECR Repository",
            export_name="ECRRepositoryURL"
        )


        # FsX Environment

        fsx_security_group = ec2.SecurityGroup(
            self,
             f"{resource_prefix}-fsx-sg",
            vpc=network_stack.vpc,
            allow_all_outbound=True,
            security_group_name=f"{resource_prefix}-fsx-sg",
        )

        fsx_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(network_stack.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(988),
            description=f"{resource_prefix}-fsx-sg-rule",
        )


        fsx_filesystem = fsx.LustreFileSystem(self, f"{resource_prefix}-fsx",
            vpc=network_stack.vpc,
            vpc_subnet=network_stack.vpc.private_subnets[0],
            storage_capacity_gib=1200,
            security_group = fsx_security_group,
            removal_policy=REMOVAL_POLICY,
            lustre_configuration={
            "per_unit_storage_throughput":50,
            "data_compression_type" : fsx.LustreDataCompressionType.LZ4,                
            "deployment_type": fsx.LustreDeploymentType.PERSISTENT_1,
            "export_path": f"s3://{AWS_BUCKET}/",
            "import_path": f"s3://{AWS_BUCKET}/",
            "auto_import_policy": fsx.LustreAutoImportPolicy.NEW_CHANGED_DELETED
            }
        )

        # Output the FSx FileSystem ID
        CfnOutput(self, "FSxFileSystemID",
            value=fsx_filesystem.file_system_id,
            description="The ID of the FSx FileSystem",
            export_name="FSxFileSystemID"
        )



        # Create Launch Template

        fsx_user_data = f"""MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="==MYBOUNDARY=="

--==MYBOUNDARY==
Content-Type: text/cloud-config; charset="us-ascii"

runcmd:
- fsx_directory=/fsx
- amazon-linux-extras install -y lustre2.10
- mkdir -p ${{fsx_directory}}
- mount -t lustre {fsx_filesystem.file_system_id}.fsx.{AWS_REGION}.amazonaws.com@tcp:/{fsx_filesystem.mount_name} ${{fsx_directory}}
 
--==MYBOUNDARY==--
"""


        commands_user_data = ec2.UserData.for_linux()
        commands_user_data.add_commands(fsx_user_data)

        fsx_lt = ec2.LaunchTemplate(
            self,
            f"{resource_prefix}-launch-template-batch",
            launch_template_name=f"{resource_prefix}-launch-template-batch",
            user_data = commands_user_data,
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            detailed_monitoring = True,
            require_imdsv2 =True,
            role = batch_instance_role,
            block_devices = [ec2.BlockDevice(
                        device_name="/dev/xvdcz",
                        volume=ec2.BlockDeviceVolume.ebs(EBS_VOL_SIZE)                                                              
                    )
                    ]

        )


        # Output the EC2 Launch Template ID
        CfnOutput(self, "EC2LaunchTemplateID",
            value=fsx_lt.launch_template_id,
            description="The ID of the EC2 Launch Template",
            export_name="EC2LaunchTemplateID"
        )

 


        # Create Batch Compute Environment
        self.compute_environment =  batch.ManagedEc2EcsComputeEnvironment(self, f"{resource_prefix}-batch-compute",
            vpc=network_stack.vpc,
            #spot=True,
            #spot_bid_percentage=COMPUTE_BID_PERCENT,
            allocation_strategy=batch.AllocationStrategy.BEST_FIT_PROGRESSIVE,
            minv_cpus= COMPUTE_MIN_CPU,
            maxv_cpus= COMPUTE_MAX_CPU,
            instance_classes=[INSTANCE_CLASS],
            vpc_subnets=ec2.SubnetSelection(subnets=network_stack.vpc.private_subnets),  
            instance_role=batch_instance_role,
            security_groups=[network_stack.sg, fsx_security_group],               
            # desiredv_cpus=COMPUTE_MIN_CPU,            
            launch_template= fsx_lt,
            terminate_on_update = False ,
            update_to_latest_image_version = True,
            update_timeout = Duration.minutes(30),
            enabled = True

        )
        self.compute_environment.node.add_dependency(fsx_lt)

           
        self.job_queue_compute_environment = batch.JobQueue(self, f"{resource_prefix}-batch-compute-queue-1",
            priority=1
        )
        self.job_queue_compute_environment.add_compute_environment(self.compute_environment, 1)



        # Output the Batch Compute Environment ARN
        CfnOutput(self, "BatchComputeEnvironmentARN",
            value=self.compute_environment.compute_environment_arn,
            description="The ARN of the Batch Compute Environment",
            export_name="BatchComputeEnvironmentARN"
        )

        # Output the Batch Job Queue ARN
        CfnOutput(self, "BatchJobQueueARN",
            value=self.job_queue_compute_environment.job_queue_arn,
            description="The ARN of the Batch Job Queue",
            export_name="BatchJobQueueARN"
        )



        # Create Fargate Environment
        self.fargate_environment = batch.FargateComputeEnvironment(self, f"{resource_prefix}-batch-fargate",
            vpc=network_stack.vpc,
            spot=True,
     
        )
        self.job_queue_fargate_environment = batch.JobQueue(self, f"{resource_prefix}-batch-fargate-queue-fargate",
            priority=1
        )
        self.job_queue_fargate_environment.add_compute_environment(self.fargate_environment, 1)
 

        # Create Host Volume
        host_volume = batch.HostVolume(
            container_path="/fsx",
            name="fsx",

            # the properties below are optional
            host_path="/fsx",
            readonly=False
        )        



       # Job definition 1
        job_definition_compute = batch.EcsJobDefinition(self, f"{resource_prefix}-batch-job-def",
            timeout = Duration.seconds(JOB_TIMEOUT),
            retry_attempts=3,
            container=batch.EcsEc2ContainerDefinition(self, f"{resource_prefix}-batch-container-def",
                image = docker_container_image,
                cpu =  JOB_CPU,
                memory = core.Size.mebibytes(JOB_MEMORY),
                privileged= True,   
                execution_role=batch_instance_role,
                job_role = batch_instance_role,
                volumes=[host_volume],
                logging=ecs.LogDrivers.aws_logs(
                    stream_prefix=f"{LOG_GROUP_NAME}",
                ),                

                 environment={
                                                    "AWS_REGION":  AWS_REGION,
                                                    "APP_NAME" : f"{APP_NAME}",
                                                    "SQS_QUEUE_URL" : self.queue.queue_url,                                               
                                                    "AWS_BUCKET" : str( AWS_BUCKET),
                                                    "LOG_GROUP_NAME" : f"{LOG_GROUP_NAME}",
                                                    "REQUIREMENTS_FILE" : str(REQUIREMENTS_FILE), 
                                                    "INPUT" : "input", 
                                                    "OUTPUT" : "output",                                                     
                                                    "PIPELINE" : "pipeline.cppipe"                                              
                                                    
                },                           
            
            ),

    
        )


        # Output the Batch Job Definition ARN
        CfnOutput(self, "BatchJobDefinitionARN",
            value=job_definition_compute.job_definition_arn,
            description="The ARN of the Batch Job Definition",
            export_name="BatchJobDefinitionARN"
        )



       # Job definition 2 for Fargate
        job_definition_fargate = batch.EcsJobDefinition(self, f"{resource_prefix}-batch-fargate-job-def-2",                                                                     
            timeout = Duration.seconds(JOB_TIMEOUT),
            retry_attempts=3,
            container=batch.EcsFargateContainerDefinition(self, f"{resource_prefix}-fargate-container-def-2",
                image = docker_container_image,
                cpu =  1,
                memory = core.Size.mebibytes(4096),
                execution_role=batch_instance_role,
                readonly_root_filesystem=False,
                assign_public_ip=False,                
                job_role = batch_instance_role,

                logging=ecs.LogDrivers.aws_logs(
                    stream_prefix=f"{LOG_GROUP_NAME}",
                ),                

                 environment={
                                                    "AWS_REGION":  AWS_REGION,
                                                    "APP_NAME" : f"{APP_NAME}",
                                                    "SQS_QUEUE_URL" : self.queue.queue_url,                                               
                                                    "AWS_BUCKET" : str(AWS_BUCKET),
                                                    "LOG_GROUP_NAME" : f"{LOG_GROUP_NAME}",
                                                    "REQUIREMENTS_FILE" : str(REQUIREMENTS_FILE), 
                                                    "INPUT" : "input", 
                                                    "OUTPUT" : "output",                                                     
                                                    "PIPELINE" : "pipeline.cppipe"                                              
                                                    
                },                           
            
            )
        )

 

        # Create an IAM role for the Lambda function
        lambda_role = iam.Role(self, f"{resource_prefix}-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
                ]
        )
        # Add a custom policy to Lambda role for Batch, Logs and S3 permissions
        lambda_policy = iam.Policy(self, f"{resource_prefix}-lambda-custom-policy",
            statements=[
                # For Batch
                iam.PolicyStatement(
                    actions=[
                        'batch:SubmitJob',
                        'batch:CancelJob',
                        'batch:DescribeJobs',
                        'batch:RegisterJobDefinition',
                        'batch:TerminateJob',
                    ],
                    resources=[
                        
                               self.compute_environment.compute_environment_arn, 
                               self.job_queue_compute_environment.job_queue_arn,
                               job_definition_compute.job_definition_arn,
                               self.fargate_environment.compute_environment_arn, 
                               self.job_queue_fargate_environment.job_queue_arn,
                               job_definition_fargate.job_definition_arn,                               

                               ],
                ),
                
            ]
        )
        lambda_policy.attach_to_role(lambda_role)


        # # cdk nag to suppress wildcard permissions
        # lambda_policy.node.add_metadata('cdk_nag', {
        #     'rules_to_suppress': [{
        #         'id': 'AwsSolutions-IAM5',
        #         'reason': 'The use of wildcard permissions is acknowledged and accepted in this context.',
        #         'applies_to': [
        #             'Resource::arn:aws:s3:::{AWS_BUCKET}/*', 
        #             'Resource::arn:aws:logs:{AWS_REGION}:{self.account}:log-group:{LOG_GROUP_NAME}:*']
        #     }]
        # })



        # Create a Lambda function to process messages from the SQS queue
        function = lambda_.Function(self, f"{resource_prefix}-process-sqs",
            runtime=lambda_.Runtime.PYTHON_3_8,
            handler="lambda-handler.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=lambda_role,
            environment={
                "BATCH_JOB_QUEUE": self.job_queue_compute_environment.job_queue_arn
            }
        )
        

        # Grant the Lambda function permission to read messages from the SQS queue
        self.queue.grant_consume_messages(function)        
        
        #Create an SQS event source for Lambda
        sqs_event_source = lambda_event_source.SqsEventSource(self.queue)

        #Add SQS event source to the Lambda function
        function.add_event_source(sqs_event_source)
        
        # Add environment variables to the Lambda function to pass to the AWS Batch job
        function.add_environment("BATCH_JOB_DEFINITION", job_definition_compute.job_definition_arn)
        function.add_environment("BATCH_JOB_NAME", f"{resource_prefix}-job-default")
        function.add_environment("BATCH_JOB_ATTEMPTS", str(JOB_ATTEMPTS))
        function.add_environment("BATCH_JOB_MEMORY", str(JOB_MEMORY))
        function.add_environment("BATCH_JOB_VCPUS", str(JOB_CPU))        
        function.add_environment("AWS_BUCKET", str(AWS_BUCKET))      
        function.add_environment("QUEUE_URL", self.queue.queue_url) 


        # Output the Lambda Function ARN
        CfnOutput(self, "LambdaFunctionARN",
            value=function.function_arn,
            description="The ARN of the Lambda function",
            export_name="LambdaFunctionARN"
        )

        

   
        




