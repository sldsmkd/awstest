image_id ='ami-000000'
instance_type = 't3.micro'
vpc_id = 'vpc-000000'
subnet_ids = ['subnet-000000', 'subnet-000001', 'subnet-000002']
autoscaling_min = 1
autoscaling_max = 3
autoscaling_desired = 1

from troposphere import Ref, Tags, Template
from troposphere.autoscaling import AutoScalingGroup, LaunchConfiguration, Metadata
from troposphere.ec2 import SecurityGroup, SecurityGroupIngress
from troposphere.ec2 import Subnet, VPC

template = Template()
template.description = "A simple load balanced application"
template.version = "2010-09-09"

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

print(template.to_json())
