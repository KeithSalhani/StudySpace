<!-- image -->

## SNDBA: Module Intro

Systems and Database Administration

## What is a Database?

We can answer this by asking what it does…

A database is a glorified file manager

It allows users to insert, delete, update, and search information held on a computer

## History of Databases

Prior to 1960 computers used magnetic tape storage instead of hard disks

In the 1960s databases emerged around the same time as magnetic disk storage (HDDs)

Earliest databases, navigational databases worked through links, like browsing the internet without Google

The modern table-oriented relational database developed by E.F. Codd in 1970. Eventually resulted in IBM'S System R in 1974

<!-- image -->

## Goals of Relational Database

Physical Data Independence

Query Optimization

Authorization

Distribution Independence

Concurrency

## Physical Data Independence

Data is presented to the user logically (tables)

The user has no knowledge of how the data is stored (files on disk)

We can change the underlying storage mechanism without affecting the database

## Query Optimization

Users retrieve data from the Database using SQL

SQL uses set notation from mathematics to describe the information the use wants to see

There are many different ways to retrieve the same set of data. Some versions may run quicker than others

It should not be the user's job to find the optimal query

```
1 SELECT FROM Departments d 2 INNER JOIN Employees e 3 ON e.deptID 二 d.deptID WHERE e.name LIKE %JACK%
```

```
L SELECT ￥ FROM Employees e 2 INNER JOIN Departments 3 ON e.deptID 二 d.deptID 4 WHERE e.name LIKE %JACK%
```

## Authorization (and Authentication)

Databases are intended to share data

Not everyone should have the same access to data

Every relational system provides tools for Authorization (restricting access based on user identity) and Authentication (ensuring a user is who they say they are)

## Distribution Independence

Becoming more and more important in recent years

Database systems can be made up of multiple computers on a network

It is the job of the system to act like only a single computer is acting as the database server

## Concurrency

Databases should allow multiple users to access data at the same time

However, they should act as though only a single user is on the system

Prevents users' queries from interfering with each other

## DB From a User's Point of View

<!-- image -->

- From an end user's point of view the database is a magic box
- SQL in, Data out

## DB from a DBA's Point of View

- All those concerns haven't magically gone away
- Whatever the user doesn't have to worry about is the DBA's job to make work

<!-- image -->

## Responsibilities of a DBA

Determine the system requirements both in terms of hardware and software

Install and Configure the operating system and database

Maintain operation of the database and the operating system on which it runs

Secure the database and carry out audits to prevent unauthorised access

Optimise the database through indexes, partitioning etc.

Bring the database online in case of failure, maintain a backup and recovery plan to prevent data loss

## Popular RDBMS's

Oracle SQL: Proprietary, feature-rich, expensive

Microsoft SQL: Proprietary, feature-rich, expensive

MySQL: Open-Source (kind-of), Free (kind-of)

Maria DB: Open-Source fork of MySQL

PostgreSQL: Open-source, feature-rich, free

## History of PostgreSQL

- The Ingres project was a database system developed at UC Berkeley in the 1980's
- Ingres developed into proprietary software and PostgreSQL was developed as an open-source improvement over the original
- Focuses on SQL compliance, extensibility
- Most popular open-source database in use today

<!-- image -->

## Database - More than a file manager

<!-- image -->

## Structure of the Module - Format

Lecture - 1 Hour: Theory-focused [2pm Wednesday]

Lab - 2 Hours: Practical-focused [To be held on the following Tuesday]

Tutorial - 1 Hour (not every week): Support-focused ['']

## Structure of the Module - Topics

- Architecture
- Securing the Database
- Optimising Queries
- Backup and Recovery
- Transactions
- Distributed Databases
- Eventual Consistency

## Structure of the Module - Assessment

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

Exam (50%)

Assignment (25%) Week 7 (TBC)

Online Quiz - Short Format MCQ (15%) Week 11 (TBC)

Labs (10%) Ongoing