# CloudStax NoSQL DB for Cassandra on the AWS Cloud

This Quick Start deploys CloudStax NoSQL DB for Cassandra into an AWS Cloud configuration of your choice.

CloudStax NoSQL DB is a NoSQL DB for [Apache Cassandra](http://cassandra.apache.org/) that makes it easy to set up, manage, and scale Apache Cassandra on AWS. Apache Cassandra is a master less peer-to-peer distributed system. Apache Cassandra is designed to handle large amounts of data across many commodity servers, providing high availability with no single point of failure. CloudStax NoSQL DB for Cassandra removes the complexity associated with deploying and managing Apache Cassandra. It provides a high-performance, highly scalable, and cost-effective NoSQL database that you can use to manage large amounts of data.

CloudStax NoSQL DB runs Apache Cassandra in a container on AWS. This deployment uses Amazon ECS for container orchestration and [CloudStax FireCamp](https://github.com/cloudstax/firecamp) for stateful service management. Each Cassandra container has one Amazon EBS volume for the commit log and one EBS volume for data. Each Cassandra container also has a unique DNS name, so an application can simply access Cassandra by using the DNS name.

Deploying CloudStax NoSQL DB on AWS enhances the reliability of using Cassandra for your production deployments. The benefits of running CloudStax NoSQL DB for Cassandra on AWS include the following:

* Cassandra nodes are deployed across multiple Availability Zones for high availability.
* The Multi-AZ environment on AWS provides automatic failure detection and recovery. If one Cassandra node fails, the AWS Auto Scaling group starts a new node, and the container service (Amazon ECS) automatically starts the service container. FireCamp attaches the original EBS volumes and update the DNS record. The failover involves no data copy and is seamless to the application.
* AWS helps provide enhanced security and isolation for Cassandra.

The AWS CloudFormation templates included with the Quick Start automate the following:

- Deploying Redis into a new VPC
- Deploying Redis into an existing VPC
