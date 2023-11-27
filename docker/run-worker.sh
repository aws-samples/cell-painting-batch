#!/bin/bash

# Define a function to print and log messages
log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') : $1"
}

# Start Script
log "Starting script..."

# Checking if necessary environment variables are set
if [ -z "$AWS_REGION" ] || [ -z "$AWS_BUCKET" ] || [ -z "$INPUT" ] || [ -z "$OUTPUT" ] || [ -z "$PIPELINE" ]; then
    log "Please set the necessary environment variables (AWS_REGION, AWS_BUCKET, INPUT, OUTPUT, PIPELINE)."
    exit 1
fi

log "Region: $AWS_REGION"
log "Bucket: $AWS_BUCKET"

#  Setup

# Mounting FsX for Lustre
log "Mounting FsX for Lustre..."

# FSx Lustre file system configuration
MOUNT_PATH="/fsx" # Update this with your actual mount path

# Checking the current directory
CURRENT_DIR=$(pwd)
if [ $? -ne 0 ]; then
    log "Failed to fetch the current directory."
    exit 1
fi
log "Current directory: $CURRENT_DIR"

# Listing objects in Lustre file system
if [ ! -d "$MOUNT_PATH" ]; then
    log "Mount path does not exist. Please verify the mount path."
    MOUNT_PATH = "s3://$AWS_BUCKET"
    exit 1
fi
log "Listing objects in Lustre file system:"
ls $MOUNT_PATH


# Create a unique temporary directory under FSx for this execution
# Append a timestamp and a random number to the directory name to make it unique
TEMP_OUTPUT_PATH_NAME="temp_$(date +%Y%m%d%H%M%S)_$RANDOM"
TEMP_OUTPUT_PATH="$MOUNT_PATH/$TEMP_OUTPUT_PATH_NAME"
mkdir -p $TEMP_OUTPUT_PATH
if [ $? -ne 0 ]; then
    log "Failed to create a unique temporary directory under FSx."
    exit 1
fi
log "Unique temporary directory created: $TEMP_OUTPUT_PATH"

log "Listing objects in Lustre file system:"
ls $MOUNT_PATH

# Set paths in the Lustre file system
INPUT_PATH="$MOUNT_PATH/$INPUT"
OUTPUT_PATH="$MOUNT_PATH/$OUTPUT"
PIPELINE_PATH="$MOUNT_PATH/$PIPELINE"

log "Input path: $INPUT_PATH"
log "Output path: $OUTPUT_PATH"
log "Pipeline path: $PIPELINE_PATH"
log "Temperory output path: $TEMP_OUTPUT_PATH"



# Running CellProfiler with input and output directories, and metadata file
log "Running CellProfiler..."
if ! cellprofiler -c -r -p $PIPELINE_PATH -o $TEMP_OUTPUT_PATH -i $INPUT_PATH; then
    log "Failed to run CellProfiler. Please check the paths and permissions."
    exit 1
fi
log "CellProfiler run completed successfully."

# List files in output location
log "Listing files in output location:"
if [ ! -d "$TEMP_OUTPUT_PATH" ]; then
    log "Output path does not exist. Please check the output path."
    exit 1
fi
ls $TEMP_OUTPUT_PATH

# Upload output files to S3
log "Upload output files to S3"
if ! aws s3 cp $TEMP_OUTPUT_PATH s3://$AWS_BUCKET/$OUTPUT --recursive; then
    log "Failed to upload output files to S3. Please check the S3 bucket and permissions."
    exit 1
fi

# Delete output directory after copying to S3
log "Deleting output files after successful copy to S3..."
if ! rm -rf $TEMP_OUTPUT_PATH; then
    log "Failed to delete the output directory: $TEMP_OUTPUT_PATH. Please check the permissions."
    exit 1
fi
log "Successfully deleted output directory after copy to S3."


log "Script completed successfully."
