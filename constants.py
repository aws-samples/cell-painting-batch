from aws_cdk import Environment
import aws_cdk as core
import aws_cdk.aws_ec2 as ec2
import os

# Define the development environment
DEV_ENV = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])
DEV_CONFIG = {
    # GENERAL SETTINGS:
    "NAME_PREFIX": 'cpb',
    "AWS_REGION": 'us-east-1',
    "REMOVAL_POLICY": core.RemovalPolicy.DESTROY,
    "AUTO_DELETE_OBJECTS":True,
    # Compute INFORMATION:
    "COMPUTE_MIN_CPU": 0,  
    "COMPUTE_MAX_CPU": 500,
    "COMPUTE_BID_PERCENT": 75,
    "INSTANCE_CLASS": ec2.InstanceClass.C4,  
    "EBS_VOL_SIZE": 100,   
    # DOCKER INSTANCE RUNNING ENVIRONMENT:
    "JOB_CPU": 4,  
    "JOB_MEMORY": 4096,    
    "JOB_ATTEMPTS": 3, 
    "JOB_TIMEOUT": 1500, 
    # SQS QUEUE INFORMATION:
    "SQS_MESSAGE_VISIBILITY": 1200, # Timeout (secs) for messages  
    # PLUGINS
    "REQUIREMENTS_FILE": '/files/requirements.txt', # Path within the CellProfiler-plugins repo to a requirements file
}
 
 
 