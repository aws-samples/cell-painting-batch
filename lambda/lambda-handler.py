import boto3
import json
import os
import logging

# Initialize AWS clients
sqs_client = boto3.client('sqs')
batch_client = boto3.client('batch')

# List of environment variable keys that are expected to be set
ENV_KEYS = [
    'BATCH_JOB_NAME',
    'BATCH_JOB_DEFINITION',
    'BATCH_JOB_QUEUE',
    'BATCH_JOB_ATTEMPTS',
    'BATCH_JOB_MEMORY',
    'BATCH_JOB_VCPUS',
    'AWS_BUCKET',
    'QUEUE_URL'
]

# Configure logging
logging.basicConfig(level=logging.INFO)


def validate_env_vars():
    """
    Validate that all required environment variables are set.
    """
    for key in ENV_KEYS:
        if key not in os.environ:
            logging.error(f"Environment variable {key} not set")
            return False
    return True


def submit_job_to_batch(message):
    """
    Submit a job to AWS Batch using message content as parameters.
    """
    job_name = os.environ['BATCH_JOB_NAME']
    job_attempts = int(os.environ['BATCH_JOB_ATTEMPTS'])
    pipeline = message['pipeline']
    input = message['input']
    output = message['output']

    job_definition = message.get('job_definition', os.environ['BATCH_JOB_DEFINITION'])
    job_queue = message.get('job_queue', os.environ['BATCH_JOB_QUEUE'])

    # Check for optional parameters in the message
    memory = message.get('job_memory', os.environ.get('BATCH_JOB_MEMORY'))
    vcpus = message.get('job_vcpu', os.environ.get('BATCH_JOB_VCPUS'))

    container_overrides = {
        'environment': [
            {'name': 'INPUT', 'value': input},
            {'name': 'OUTPUT', 'value': output},
            {'name': 'PIPELINE', 'value': pipeline},
        ],
        "resourceRequirements": [
            {
                "type": "MEMORY",
                "value": memory
            },
            {
                "type": "VCPU",
                "value": vcpus
            }
        ],        
    }

    # if memory and vcpus:
    #     container_overrides['memory'] = memory
    #     container_overrides['vcpus'] = vcpus

    response = batch_client.submit_job(
        jobName=job_name,
        jobDefinition=job_definition,
        jobQueue=job_queue,
        containerOverrides=container_overrides,
        retryStrategy={
            'attempts': job_attempts
        }
    )
    logging.info(f"Job submitted: {response}")


def delete_message_from_sqs(record):
    """
    Delete the processed message from the SQS queue.
    """
    receipt_handle = record['receiptHandle']
    sqs_client.delete_message(
        QueueUrl=os.environ['QUEUE_URL'],
        ReceiptHandle=receipt_handle
    )


def handler(event, context):
    """
    Lambda function entry point.
    """
    if not validate_env_vars():
        logging.error("Required environment variables are not set.")
        return

    for record in event['Records']:
        try:
            parsed_data = json.loads(record['body'])

            # If the parsed data is a list, iterate over each message
            if isinstance(parsed_data, list):
                for message in parsed_data:
                    try:
                        submit_job_to_batch(message)
                    except Exception as e:
                        logging.error(f"Failed to submit job: {e}")
            # If the parsed data is a dictionary, process it directly
            elif isinstance(parsed_data, dict):
                try:
                    submit_job_to_batch(parsed_data)
                except Exception as e:
                    logging.error(f"Failed to submit job: {e}")
            else:
                logging.error(f"Unexpected message format: {parsed_data}")

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse message: {e}")
            continue

        try:
            delete_message_from_sqs(record)
        except Exception as e:
            logging.error(f"Failed to delete message from SQS: {e}")
