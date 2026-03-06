<!-- image -->

## Security in the Database

SNDBA: Part 2

## Users, Roles, Privileges

<!-- image -->

## Users and Privileges

<!-- image -->

Account name to login and perform different actions in Database

1. A Schema is a collection of database objects owned by a database us
3. Schema is a logical structure.
2. Schema name is same as the username.
1. Cannot create two account/schema of the same name.
3. A user needs privileges to create objects and perform different actions in the database.
2. Schema is empty after the creation of an account.

## Users, Groups, Roles

Traditional Security Architecture: Users and Groups

User = login, users can be granted privileges

Group = usually no login, can be granted privileges

Users &lt;-&gt; Groups = Many-to-many

<!-- image -->

Postgres merges users and groups into roles

## Roles in Postgres

A fresh installation of Postgres comes with a single login-enabled role with super-user privileges, postgres

As a super-user, should be used minimally

Connecting with the postgres role will allow you to manage and create additional roles

## Privileges

Users with superuser privilege can do activities in the database.

User who creates the table owns the table and he can only see or modify the data other than superusers.

Other users who want to view the data in tables owned by others need privileges on the table.

## Privileges

Table

Select

Insert

Update

Delete

Function

Execute

Procedure Languages

Usage

User

Superuser

CreateDB

CreateRole

Login

<!-- image -->

## Managing Roles

Each role name must be unique within a database cluster.

You can get a list of existing roles through the pg\_roles system catalog

SELECT rolname FROM pg\_roles;

You can create and drop roles using SQL commands

CREATE ROLE &lt;rolename&gt;

DROP ROLE &lt;rolename&gt;

## Role Attributes

<!-- image -->

## Role Attributes

| Attribute         | Description                                                               | Keyword    |
|-------------------|---------------------------------------------------------------------------|------------|
| Login Privilege   | Allows this role to be the initial role name for a db connection          | LOGIN      |
| Superuser Status  | Superusers by-pass all security checks. Should be used sparingly          | SUPERUSER  |
| Database Creation | Needed to create databases                                                | CREATEDB   |
| Role Creation     | Allows this role to create, alter and drop other roles (except Superuser) | CREATEROLE |

Each keyword can be negated by putting NO before it,

LOGIN/NOLOGIN, SUPERUSER/NOSUPERUSER

ALTER ROLE &lt;rolename&gt; &lt;keyword1&gt; &lt;keyword2&gt;

## Creating a Role for a User

A user role needs to be able to connect to the database, login and supply a password to authenticate themselves

If a password is not supplied for a user all login attempts will fail

CREATE ROLE Ali LOGIN WITH PASSWORD 'password';

## PostgreSQL Documentation

The PgSQL documentation contains everything you will ever need to know about installing, maintaining and working with a database https://www.postgresql.org/docs/current/index.html

```
ALTER ROLE role_specification[WITH ]option[...] where optioncanbe: SUPERUSER|NOSUPERUSER |CREATEDB丨NOCREATEDB 丨CREATEROLE 丨 NOCREATEROLE I INHERIT 丨 NOINHERIT 丨LOGIN 丨NOLOGIN IREPLICATION|NOREPLICATION IBYPASSRLS|NOBYPASSRLS ICONNECTIONLIMITconnlimit |VALID UNTIL'timestamp' ALTERROLEnameRENAMETOnew_name ALTER ROLE{role_Specification|ALL}[ IN DATABASE database_name]SET configuration_parameter{ TO|=}{value丨DEFAULT} ALTERROLE{role_specification|ALL}[IN DATABASE database_name]RESETconfiguration_parameter ALTERROLE{role_specification|ALL}【IN DATABASE database_name]RESET ALL whererole_specificationcanbe: role_name |CURRENT_ROLE |CURRENT_USER ISESSION_USER
```

## Group Roles

Group roles

: no real distinction but used informally

Group roles usually don't have a login, but are granted to other roles

CREATE ROLE Ali LOGIN;

CREATE ROLE administrators NOLOGIN CREATEDB CREATEROLE;

GRANT administrators TO Ali;

## Role Inheritance

Roles can be specified with the INHERIT or NOINHERIT keyword

This controls what happens when the role is granted membership of a group role .

Without INHERIT, a role must explicitly "become" the granted role to use it (SET ROLE command)

With INHERIT, the role directly inherits all privileges of the granted role and doesn't need to explicitly invoke the role.

## Inheritance in Action

```
CREATE ROLE jOe LOGIN INHERIT; CREATE 三 ROLE admin NOINHERIT; CREATE ROLE wheel NOINHERIT; GRANT admin TO joe; GRANT wheel TO admin;
```

Which privileges has Joe automatically inherited?

<!-- image -->

## Inherit and Noinherit

<!-- image -->

Create Role Role1; Create Role Role2; Grant Role1 to Role2; Grant Role2 to User1;

Does User1 has privileges of Role1?

Depends on whether Role2 is created with inherit or noinherit option. If it is created with inherit option, then user1 will have privileges assigned to Role1.

## Dropping Roles

What's gone wrong?

<!-- image -->

## Handling Dependencies when Dropping Roles

A role may not be dropped while it has ownership of any database objects

Objects ownership may be manually reassigned one step at a time

ALTER TABLE testtable OWNER TO postgres;

## REASSIGN OWNED

If a role owns many objects, manually reassigning can be time-consuming

PgSQL lets us transfer ownership of all objects using the REASSIGN OWNED command

REASSIGN OWNED BY Ali TO postgres; DROP OWNED BY Ali; DROP ROLE Ali;

After reassigning owned, we need to drop owned to take care of privileges granted on objects which do not belong to the role (order is very important!)

## Pre-Defined Roles

| pg_read_all_data   | Read all data (tables, views, sequences), as if having SELECT rights on those objects, and USAGE rights on all schemas, even without having it explicitly. This role does not have the role attribute BYPASSRLS set. If RLS is being used, an administrator may wish to set BYPASSRLS on roles which this role is GRANTed to.                      |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| pg_write_all_data  | Write all data (tables, views, sequences), as if having INSERT, UPDATE, and DELETE rights on those objects, and USAGE rights on all schemas, even without having it explicitly. This role does not have the role attribute BYPASSRLS set. If RLS is being used, an administrator may wish to set BYPASSRLS on roles which this role is GRANTed to. |

## Pre-Defined Roles

| pg_read_all_settings   | Read all configuration variables, even those normally visible only to superusers.                                                               |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| pg_read_all_stats      | Read all pg_stat_* views and use various statistics related extensions, even those normally visible only to superusers.                         |
| pg_stat_scan_tables    | Execute monitoring functions that may take ACCESS SHARE locks on tables, potentially for a long time.                                           |
| pg_monitor             | Read/execute various monitoring views and functions. This role is a member of pg_read_all_settings, pg_read_all_stats and pg_stat _scan_tables. |

## Pre-Defined Roles

| pg_database_owner         | None. Membership consists, implicitly, of the current database owner.                                                                                       |
|---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| pg_signal_backend         | Signal another backend to cancel a query or terminate its session.                                                                                          |
| pg_read_server_files      | Allow reading files from any location the database can access on the server with COPY and other file-access functions.                                      |
| pg_write_server_files     | Allow writing to files in any location the database can access on the server with COPY and other file-access functions.                                     |
| pg_execute_server_program | Allow executing programs on the database server as the user the database runs as with COPY and other functions which allow executing a server-side program. |

## Databases, Schemas and Objects

Security in the Database

## Database Objects

A database consists of objects

: tables, views, schemas, functions etc.

Each database object has an owner : (default = creator)

An object owner can grant privileges on an object: SELECT, UPDATE, DELETE, EXECUTE

Privileges granted WITH GRANT OPTION allow the recipient to pass these privileges onto others

## Schemas and Tablespaces

Schemas provide a logical separation of database objects

Each table, view, function etc. belongs to a database schema

Tablespaces provide a physical separation of objects

Tablespaces correspond to files in the operating system which hold the data in tables and indexes

By default, new database objects use the pg\_default tablespace

## Schemas and Tables

The fully qualified name for an object includes both the database and schema in which the object resides &lt;database&gt;.&lt;schema&gt;.&lt;table&gt;

Each database has a search\_path which gives a list of schemas to be checked if the fully qualified name is not provided ("default" schemas)

The search\_path can be altered using the ALTER DATABASE command

ALTER DATABASE &lt;dbname&gt; SET search\_path TO schema1, schema2, schema3;

## Minimum Privileges

In order to connect to a database, a role needs the CONNECT privilege GRANT CONNECT ON &lt;database&gt; TO &lt;role&gt;

In order to use a schema, a role needs the USAGE privilege GRANT USAGE ON &lt;schema&gt; TO &lt;role&gt;

## The CREATE Privilege

The CREATE privilege allows users to create new objects in a database

Granting CREATE on a database allows users to create new schemas

Granting CREATE on a schema allows users to create new db objects (provided they have USAGE)

Granting CREATE on a tablespace allows users to create tables, indexes and temporary files within the tablespace

## Privileges assigned directly to users

<!-- image -->

…

## Privileges assigned via Role to Users

<!-- image -->

## Object-Level Privileges

Each object within a database has its own privileges

Tables require the SELECT, UPDATE, INSERT, DELETE privileges for full access

SELECT privilege is required to make proper use of UPDATE and DELETE The TRIGGER privilege allows users to write custom code in response to an insert, update or delete on a table.

The ALL keyword allows all privileges for an object to be deleted at once

## Cascading Revoke

We saw that a privilege can be granted with GRANT OPTION

This allows the grantee to pass that privilege on to other roles

Alice -&gt; USAGE on cheshire to BOB with GRANT OPTION

Bob's privilege is now dependent on Alice's

We cannot revoke Alice's privilege while Bob's exists in the database

## Cascading Revoke

REVOKE &lt;privilege&gt; ON &lt;object&gt; FROM &lt;role&gt; CASCADE|RESTRICT

The CASCADE keyword automatically revokes all privileges granted with GRANT OPTION

The RESTRICT keyword produces an error message if any such privileges exist

## Row Level Security

Security in the Database

## Without RLS

<!-- image -->

## With RLS

<!-- image -->

## Row-Level Security (RLS)

SQL standard: permissions on database objects (tables, views)

Row-Level Security: Additional Feature, fine-grained control on tables

RLS uses Policies : like an extra WHERE clause, must return TRUE of FALSE

Often uses current\_user variable, returning current user's username

## Row Level Security Example

CREATE TABLE accounts (manager text, company text, contact\_email text);

ALTER TABLE accounts ENABLE ROW LEVEL SECURITY ;

CREATE POLICY account\_managers ON accounts TO managers USING (manager = current\_user);

## Different Operations

A policy can be declared FOR SELECT, FOR UPDATE, FOR INSERT, FOR DELETE

If not specified, the policy applies to all operations

Multiple policies are combined using OR (unless the restrictive option is used)

## What does this policy do?

```
CREATE POLICY user_sel_policy ON users FOR SELECT USING (true); CREATE POLICY user_mod_policy ON users USING (user_name = current_user);
```

## USING and WITH CHECK

RLS policies ae defined with USING and WITH CHECK clauses

A USING clause is applied for existing rows

A WITH CHECK clause is applied for new rows (update/insert)

If WITH CHECK is not declared it will be identical to USING

## Limitations

Policies are not applied when checking for referential integrity

User-Defined functions will not be evaluated before policy is enforced (unless marked LEAKPROOF)

Policy expressions can use SQL statements to check other tables but are run as the current user, so may only access tables that user has access to

## Additional Security Considerations

Security in the Database

## Password Hashing

Older versions of Postgres used the md5 hashing algorithm

Md5 is insecure, it is possible for hackers to identify passwords hashed using this algorithm

Currently Postgres uses SCRAM (Salted Challenge Response Authentication Mechanism) by default.

Postgres maintains MD5 for backward compatibility but this should not be used.

## Encryption Options

Password Encryption

Column-Specific Encryption

Data Partition Encryption

Encrypting across the Network

Two-Way Encryption

Client-Side Encryption

## Password Policy

An insecure password presents a vulnerability to the entire database

Password policies should be used to enforce strict passwords

The passwordcheck module can be used to write custom rules to determine if a password is secure enough https://www.postgresql.org/docs/current/passwordcheck.html

An expiration date can be set for a password using the ALTER ROLE command

## Listen Addresses

Database servers typically have multiple IP addresses

Public IP addresses can be reached by anyone who knows the IP address of the server

We can configure PostgresSQL to only accept connections from certain IP addresses

By default, the database will not accept any connections over the network

## Principle of Least Privilege

Good database design obeys the Principle of Least Privilege (PoLP)

PoLP states that each user should have the minimum privileges necessary to do the job they need to do.

PoLP limits the impact of a security breach on the entire database

## Principle of Least Privileges

Active

<!-- image -->

Remember: More the data More Accurate the least

privilege model be

## Summary

In this lecture we discussed

- Roles in PostgreSQL
- how they are managed
- role inheritance
- pre-defined roles
- Schemas, Tablespaces and Tables
- Privileges, privilege management and minimum privileges required
- Row-Level Security (RLS)
- Additional Security Considerations