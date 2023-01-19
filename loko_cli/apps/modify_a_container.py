from loko_cli.business.deployment.cloud.ec2 import EC2Manager

e = EC2Manager()

print(e.get_security_group("sg-d4105ba9"))
