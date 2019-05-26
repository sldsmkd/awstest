# Create an application stack in Terraform consisting of an ELB and ASG. 
# The stack should setup 
# * ASG scaling alarms, 
# * cloudwatch ELB unhealthy host alarms, 
# * IAM role & policy, 
# * ELB logs 
# * security groups.
# The instance should be able to access S3. The application should
# be a minimal application that has a status endpoint, any language.
# Please put your solution to Q10 in a public GitHub repo and share
# the link.

# "ScaleUpPolicy" : {
#    "Type" : "AWS::AutoScaling::ScalingPolicy",
#    "Properties" : {
#       "AdjustmentType" : "ChangeInCapacity",
#       "AutoScalingGroupName" : { "Ref" : "asGroup" },
#       "Cooldown" : "1",
#       "ScalingAdjustment" : "1"
#    }
# },
# "CPUAlarmHigh": {
#    "Type": "AWS::CloudWatch::Alarm",
#    "Properties": {
#       "EvaluationPeriods": "1",
#       "Statistic": "Average",
#       "Threshold": "10",
#       "AlarmDescription": "Alarm if CPU too high or metric disappears indicating instance is down",
#       "Period": "60",
#       "AlarmActions": [ { "Ref": "ScaleUpPolicy" } ],
#       "Namespace": "AWS/EC2",
#       "Dimensions": [ {
#          "Name": "AutoScalingGroupName",
#          "Value": { "Ref": "asGroup" }
#       } ],
#       "ComparisonOperator": "GreaterThanThreshold",
#       "MetricName": "CPUUtilization"
#    }
# }


image_id ='ami-000000'
instance_type = 't3.micro'
vpc_id = 'vpc-000000'
subnet_ids = ['subnet-000000', 'subnet-000001', 'subnet-000002']
autoscaling_min = 1
autoscaling_max = 3
autoscaling_desired = 1

from troposphere import Ref, Tags, Template
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration, Metadata, ScalingPolicy
from troposphere.cloudwatch import Alarm, MetricDimension
from troposphere.ec2 import SecurityGroup, SecurityGroupIngress
from troposphere.ec2 import Subnet, VPC

# Set up the base template
template = Template()
template.description = "A simple load balanced application"
template.version = "2010-09-09"


# Setup the ASG & launch config
launch_config = LaunchConfiguration(
    "LaunchConfig",
    ImageId=image_id,
    InstanceType=instance_type
)
auto_scale_group = AutoScalingGroup(
        "AutoscaleGroup",
        MinSize=autoscaling_min,
        MaxSize=autoscaling_max,
        DesiredCapacity=autoscaling_desired,
        LaunchConfigurationName=Ref(launch_config),
        VPCZoneIdentifier=subnet_ids
)
template.add_resource(launch_config)
template.add_resource(auto_scale_group)

# asg scaling policies
scale_down_policy = ScalingPolicy(
    "ScaleDownPolicy",
    AdjustmentType = "ChangeInCapacity",
    AutoScalingGroupName = Ref(auto_scale_group),
    Cooldown="300",
    ScalingAdjustment="1"
)
scale_up_policy = ScalingPolicy(
    "ScaleUpPolicy",
    AdjustmentType="ChangeInCapacity",
    AutoScalingGroupName=Ref(auto_scale_group),
    Cooldown="120",
    ScalingAdjustment="1"
)
template.add_resource(scale_down_policy)
template.add_resource(scale_up_policy)

# cloudwatch alarms on cpu
cloudwatch_cpu_high_alarm=Alarm(
    "CPUHighAlarm",
    EvaluationPeriods="2",
    Statistic="Average",
    Threshold="70",
    Period="60",
    AlarmDescription="Alarm if CPU > 70%",
    Namespace="AWS/EC2",
    Dimensions=[MetricDimension(
        Name="AutoScaleGroup",
        Value=Ref(auto_scale_group)
    )],
    AlarmActions=[Ref(scale_down_policy)],
    ComparisonOperator="LessThanThreshold",
    MetricName="CPUUtilization"
)
cloudwatch_cpu_low_alarm=Alarm(
    "CPULowAlarm",
    EvaluationPeriods="5",
    Statistic="Average",
    Threshold="30",
    Period="60",
    AlarmDescription="Alarm if CPU < 30%",
    Namespace="AWS/EC2",
    Dimensions=[MetricDimension(
        Name="AutoScaleGroup",
        Value=Ref(auto_scale_group)
    )],
    AlarmActions=[Ref(scale_down_policy)],
    ComparisonOperator="LessThanThreshold",
    MetricName="CPUUtilization"
)
template.add_resource(cloudwatch_cpu_high_alarm)
template.add_resource(cloudwatch_cpu_low_alarm)

print(template.to_yaml())
