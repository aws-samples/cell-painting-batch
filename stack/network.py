from aws_cdk import (
    Stack,
    aws_logs as logs,
    aws_ec2 as ec2,
    aws_iam as iam
)
from constructs import Construct
import aws_cdk as core
import boto3
 

class NetworkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, config, **kwargs) -> None:
        # Call the parent class's initialization method
        super().__init__(scope, construct_id, **kwargs)

        # Concatenate name_prefix with "nw" to form resource_prefix,
        # which will be used as part of the names for the resources created
        resource_prefix = f"{config['NAME_PREFIX']}-nw"

        # Set the Log Group Name
        log_group_name = f"{resource_prefix}-log"

        # Check if a Log Group with the specified name already exists,
        # If it doesn't exist, create a new Log Group
        if not self.log_group_exists(log_group_name):
            self.log_group = logs.LogGroup(
                self, f"{resource_prefix}-logs", 
                log_group_name=log_group_name,
                retention=logs.RetentionDays('ONE_YEAR'),
                removal_policy=core.RemovalPolicy('DESTROY')                                         
                )
            self.log_group_per_instance = logs.LogGroup(
                self, f"{resource_prefix}-logs-instance", 
                log_group_name=f"{log_group_name}_perInstance",
                retention=logs.RetentionDays('ONE_YEAR'),
                removal_policy=core.RemovalPolicy('DESTROY')                      
                )
            print("log  created")

        # Create a Virtual Private Cloud (VPC) with maximum availability zones set to 1
        self.vpc = ec2.Vpc(
            self, f"{resource_prefix}-vpc",
            max_azs=1
        )

        # Setup IAM user for logs
        vpc_flow_role = iam.Role(
            self, f"{resource_prefix}-vpc-flow-log-role",
            assumed_by=iam.ServicePrincipal('vpc-flow-logs.amazonaws.com')
        )        
        # Setup VPC flow logs
        vpc_log = ec2.CfnFlowLog(
            self, f"{resource_prefix}-vpc-flow-log",
            resource_id=self.vpc.vpc_id,
            resource_type='VPC',
            traffic_type='ALL',
            deliver_logs_permission_arn=vpc_flow_role.role_arn,
            log_destination_type='cloud-watch-logs',
            log_group_name=log_group_name
        )        

        # Create a Security Group within the VPC created above
        self.sg = ec2.SecurityGroup(
            self,
            f"{resource_prefix}-sec-grp",
            vpc=self.vpc,
        )

        # Output the ID of the created VPC to the CloudFormation stack outputs
        core.CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            export_name=f"{resource_prefix}-vpc",
        )

        # Output the IDs of the created subnets to the CloudFormation stack outputs
        for i, subnet in enumerate(self.vpc.private_subnets):
            core.CfnOutput(
                self,
                f"PrivateSubnet{i}",
                value=subnet.subnet_id,
                export_name=f"{resource_prefix}-subnet{i}",
            )
            
    @staticmethod
    def log_group_exists(log_group_name):
        """
        Check if a log group with the given name exists.
        This method uses the AWS SDK (Boto3) to check if a log group with the specified name exists.

        :param log_group_name: The name of the log group to check.
        :return: True if the log group exists, False otherwise.
        """
        # Initialize a Boto3 client for CloudWatch Logs
        logs_client = boto3.client('logs')
            
        try:
            # Attempt to describe log groups with the specified name prefix
            response = logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)
            
            # Check if the specific log group exists in the returned log groups
            for group in response.get('logGroups', []):
                if group['logGroupName'] == log_group_name:
                    print("log exists")
                    return True
            
            print("log doesn't exist")
            return False
        except logs_client.exceptions.ResourceNotFoundException:
            # This may not be necessary because describe_log_groups may not throw this exception
            # for missing log groups as explained earlier, but we'll keep it just in case.
            print("log doesn't exist due to exception")
            return False