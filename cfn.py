# * security groups.


image_id ='ami-000000'
instance_type = 't3.micro'
vpc_id = 'vpc-000000'
subnet_ids = ['subnet-000000', 'subnet-000001', 'subnet-000002']
autoscaling_min = 1
autoscaling_max = 3
autoscaling_desired = 1
certificate_arn = 'arn:::::000000'
bucket_arn = 'arn:aws:s3:::example.application'

from troposphere import AWSAttribute, GetAtt, Join, Ref, Tags, Template
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration, Metadata, ScalingPolicy
from troposphere.cloudwatch import Alarm, MetricDimension
from troposphere.ec2 import SecurityGroup, SecurityGroupIngress
from troposphere.ec2 import Subnet, VPC
from troposphere.iam import InstanceProfile, Policy, PolicyType, Role
from troposphere.elasticloadbalancingv2 import LoadBalancer, TargetGroup, Listener, Action, Certificate, LoadBalancerAttributes, RedirectConfig
from troposphere.s3 import Bucket, BucketPolicy

# Set up the base template
template = Template()
template.description = "A simple load balanced application"
template.version = "2010-09-09"

# IAM Role and Policy for the Instance
example_role = Role(
    "ExampleRole",
    RoleName="ExampleRole",
    AssumeRolePolicyDocument= {
        "AssumeRolePolicyDocument": {
            "Version" : "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": [ "ec2.amazonaws.com" ]
                },
                "Action": [ "sts:AssumeRole" ]
            }]
        },
        "Path": "/"
    }
)
example_policy = PolicyType(
    "ExamplePolicy",
    PolicyName="ExamplePolicy",
    PolicyDocument={
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Stmt1429136633762",
                "Action": [
                "s3:ListObjects",
                "s3:GetObject"
                ],
                "Effect": "Allow",
                "Resource": [
                    bucket_arn,
                    bucket_arn + "/*"
                ]
            }
        ]
    },
    Roles=[Ref(example_role)]
)
example_instance_profile = InstanceProfile(
    "ExampleInstanceProfile",
    Roles=[Ref(example_role)]
)
template.add_resource(example_role)
template.add_resource(example_policy)
template.add_resource(example_instance_profile)

# Setup the ASG & launch config
launch_config = LaunchConfiguration(
    "LaunchConfig",
    ImageId=image_id,
    IamInstanceProfile=Ref(example_instance_profile),
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
    AlarmActions=[Ref(scale_up_policy)],
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

logs_bucket=Bucket(
    "LogsBucket",
    DeletionPolicy="Retain"
)
logs_bucket_policy=BucketPolicy(
    "LogsBucketPolicy",
    Bucket=Ref(logs_bucket),
    PolicyDocument={
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Stmt1429136633762",
                "Action": [
                    "s3:PutObject"
                ],
                "Effect": "Allow",
                "Resource": Join("", 
                    [
                        's3:::',
                        Ref(logs_bucket),
                        "/alb/*"
                    ]
                ),
                "Principal": {
                    "AWS": Ref("AWS::AccountId")
                }
            }
        ]
    }
)
template.add_resource(logs_bucket)
template.add_resource(logs_bucket_policy)

# Create Load Balancer - need ref to sg's here
load_balancer = LoadBalancer(
    "exampleloadbalancer",
    Subnets=subnet_ids,
    LoadBalancerAttributes=[
        LoadBalancerAttributes(
                Key="access_logs.s3.enabled",
                Value="true"
        ),
        LoadBalancerAttributes(
                Key="access_logs.s3.bucket",
                Value="true"
        ),
        LoadBalancerAttributes(
                Key="access_logs.s3.prefix",
                Value="alb"
        )
    ],
    DependsOn=Ref(logs_bucket_policy)
)
template.add_resource(load_balancer)
target_group=TargetGroup(
    "exampletargetgroup",
    VpcId=vpc_id,
    Port='80',
    Protocol='HTTP'
)
listener = Listener(
    "examplelistener",
    LoadBalancerArn=Ref(load_balancer),
    Port='443',
    Protocol='HTTPS',
    Certificates=[
        Certificate(
            CertificateArn=certificate_arn
        )
    ],
    DefaultActions=[
        Action(
            Type='forward',
            TargetGroupArn=Ref(
                target_group)
        )
    ],
    SslPolicy="ELBSecurityPolicy-TLS-1-2-Ext-2018-06"
)
template.add_resource(target_group)
template.add_resource(listener)

# add a cloudwatch alarm and trigger on > 1 unhealthy hosts in the load balancer
cloudwatch_loadbalancer_hosts=Alarm(
    "UnhealthyHosts",
    EvaluationPeriods="2",
    Statistic="Minimum",
    Threshold="0",
    Period="120",
    AlarmDescription="Alarm if Unhealthy Hosts > 1",
    Namespace="AWS/ApplicationELB",
    Dimensions=[
        MetricDimension(
            Name="TargetGroup",
            Value=GetAtt(target_group, 'TargetGroupFullName')
        ),
        MetricDimension(
            Name="LoadBalancer",
            Value=GetAtt(load_balancer, 'LoadBalancerFullName')
        )        
    ],
    ComparisonOperator="GreaterThanThreshold",
    MetricName="UnHealthyHostCount"
)
template.add_resource(cloudwatch_loadbalancer_hosts)

print(template.to_yaml())
