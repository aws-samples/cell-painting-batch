import aws_cdk as core
import aws_cdk.assertions as assertions

from cell_profiler.cell_profiler_stack import CellProfilerStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cell_profiler/cell_profiler_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CellProfilerStack(app, "cell-profiler")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
