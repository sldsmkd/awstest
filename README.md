#AWS Test

##Cloudformation Stack
Cloudformation is pretty verbose and time consuming to put together, but this should meet the requirements. Caveat is that it hasn't been tested.

The requirements were to create an application stack in Terraform consisting of an ELB and ASG. _used an ALB instead here_ As agreed, cloudformation was suitable (in this case the Troposphere library was used). If you Want to run this, you'll need Python3 and the troposphere library installed. To run; `python3 app.py`

###The stack should setup:
* ASG scaling alarms _(added scale up and scale down based un cpu utilisation, scale up is more aggressive than scale down)_
* Cloudwatch ELB unhealthy host alarms
* IAM role & policy _(assume role is also needed here)_
* ELB logs _(also creates a bucket to store these)_
* Security Groups _(minimal, https allowed in from anywhere to the Load Balancer, all traffic from Load Balancer allowed to EC2 instances)_
* The instance should be able to access S3. 
* The application should be a minimal application that has a status endpoint, any language. _running an existing docker container via userdata, there is a sample app that meets the requirements_

###Improvements & Notes:
* Cloudformation is extremely verbose, a more normal development pattern would be to decompose the template into reusable components
* The template should ideally spin up its own VPC / Subnets etc, but this was out of scope
* Config should be externalised, either via Inputs or better still by a config file (yaml or similar)
* An assumption was made that the AMI has docker installed, Amazon Linux _I think_ does.
* Service discovery at template generation time can be achieved by querying the AWS SDK
* Tests should be added with assertations that the template has the correct stuff in it
* This could be easily tooled into a pipeline, extra tests should be added to check on the status when the template is executed
* This has not been tested in AWS, I ran out of time.
* There's probably some ordering issues, CFN is generally pretty code about detecting these during execution

##Example Web App
This is a trivial web application that serves up Hello World and also has a load balancer healtcheck.
It supports the following routes:
* / - Hello World!
* /status - Load Balancer STatus Check

To build do something like this:
`docker build -t exampleapp:latest .`

To run do something like this:
`docker run -p 80:5000 exampleapp:latest`

You could publish this into a repository such as Docker Hub to use this in the example cfn stack