## SYSTEMS AND DATABASE ADMINISTRATION: LAB 3

Auditing

<!-- image -->

TU Dublin TU-857

<!-- image -->

## OVERVIEW

## Current OS and Software

You should now be running PostgreSQL on an Ubuntu server. Your virtual machine should have a static IP assigned to it and you should have connectivity from the host to the guest. You should also have installed Beekeeper or an equivalent IDE on your host.

## Essential

## Today's Lab

In today's lab we're going to install a sample database, enable basic logging on the server using the built-in logging functionality. We're then going to install the pgAudit extension and enable it for more fine-grained control.

## Before we Begin

When we installed postgres, we got a whole bunch of new executable programmes (postmaster, psql etc. ) installed to the /usr/local/pgsql/bin folder. It would be handy to be able to execute these programmes without having to type the full path each time. We can do this by editing our .bash\_profile and adding the directory containing the executables to our path. Log in as the postgres user. Create a new (or edit the existing) .bash\_profile in the home directory of the postgres user. Add the following lines PATH=/usr/local/pgsql/bin:$PATH export PATH Exit out and switch back to the postgres user. Ensure the change has worked by running psql --version if you don't get a command-not-found error you're good.

## Preparing to Install the Pagila Database

The Pagila schema is based on a demo schema (Sakila) that came with MySQL and is often used to teach and talk about database techniques. Pagila has been updated to follow the styles and conventions of Postgres rather than MySQL. The scripts for the Pagila database are available on:

https://ftp.postgresql.org/pub/projects/pgFoundry/dbsamples/pagila/pagila/pagila-0.10.1.zip

1. Use the wget command to download the zip file.
2. unzip pagila-0.10.1.zip

Quick links:

## bit.ly/3xmSPYU [pagila-schema.sql] https://bit.ly/3lBzY9X [pagila-insert-data.sql]

By default, the Pagila script creates everything in the public schema. Let's change that! The sed occurrence of public. with pagila.

(stream editor) command, allows us to easily find and replace text in files from the command line. Make a backup of both files, and run the following command for each of the files to replace every sed -i 's/public\./pagila\./g' &lt;file name&gt; The scripts don't create the database objects in the right order so you'll end up running into check constraints if you try to run the files as they are. We need a way to disable all foreign keys after we create the schema and then re-enable them once the database has been created. Unfortunately, there's no easy way to turn CONSTRAINTS on or off in PGSQL so we need to drop them entirely. Luckily, all of the constraints are created at the end of the file so it's easy for us to get in and edit the code as we need to Use the tail command to skip lines until you reach the constraint definitions (search for 'ADD CONSTRAINT' to find the starting point, typically around line 1535), save the output as pagila-createconstraints.sql tail -n +1535 pagila-0.10.1/pagila-schema.sql &gt; pagila-0.10.1/pagila-create-constraints.sql Copy this file and call the copied version pagila-drop-constraints.sql. We're going to use stream editor to change the ADD CONSTRAINT statements into DROP CONSTRAINTS. sed -ri 's/ADD CONSTRAINT ([a-z0-9\_]+) .*/DROP CONSTRAINT \1;/g' pagila-drop-constraints.sql We're using regular expressions here to replace every occurrence of ADD CONSTRAINT with DROP CONSTRAINT. We capture the constraint name in round brackets on the left, and then reference it again with the \1 on the right. If successful this will alter the file in place. Save the files, we'll run

these as soon as we've configured auditing on the database. Configuring Auditing Our first step is to determine the location of the PgSQL configuration file. We can query this directly from the database. As the postgres user start the database server Connect to the database using psql and run the SHOW config\_file; command to see the location of the config file we need Exit psql and open the configuration file in your favourite text editor. Edit the following parameters

<!-- image -->

Make sure the log directory exists - it probably doesn't (the log\_directory name is relative to the pgsql data dir). Next we want to reload the configuration so our database starts logging. You may need to restart the server again first. Connect to the database using psql and issue the following command SELECT pg\_reload\_conf(); Before we run the SQL files we need to create the PAGILA schema CREATE SCHEMA pagila; - Ensure required extensions are available CREATE EXTENSION IF NOT EXISTS pgcrypto; GRANT USAGE ON SCHEMA pagila TO postgres; Disconnect from psql and check the contents of the log file. Take a screenshot.

## Creating the Database

Execute the scripts you created earlier using psql in the following order to create the database:

1. pagila-schema.sql
2. pagila-drop-constraints.sql
3. Execute pagila-insert-data.sql
4. Execute pagila-create-constraints.sql

You can execute SQL scripts either by copy/pasting them into your chosen gui and running them or by running them directly with psql. The psql command takes an -f parameter which allows you to specify a filepath. Running psql in this way will execute all commands in the file rather than giving you an interactive SQL prompt. e.g. createdb pagila psql pagila &lt; pagila-0.10.1/pagila-schema.sql [ And similarly for other sql files.] Check the log directory. How many files are there? What size are the files?

## Submission

Create a single short document containing a screenshot of the entries generated in the log file by running a CREATE TABLE command.

Include an brief explanation of what each of the log values mean.

## Demo

Demonstrate active auditing: run a CREATE TABLE command and show the resulting log entry.

=================================================================================

## Optional below here

=================================================================================

## Installing PgAudit

Next we'll install PgAudit to give us more control over our auditing.

As the root user, checkout the PgAudit git repository https://github.com/pgaudit/pgaudit/blob/master/README.md

Follow the instructions to inistall PgAudit. Note that the README tells you to check out REL\_16\_STABLE, however, the version you need depends on the version of postgres you have installed . You can check the version of PgSQL you are running by connecting to the database and running the following query

SELECT version();

Once you've installed PgAudit you'll need to enable it.

Go back to you postgresql.conf and set the shared\_preload\_libraries parameter to 'pgaudit'

Restart the database

Log in to the database and use the CREATE EXTENSION command to enable the PgAudit EXTENSION

CREATE EXTENSION pgaudit;

Configure pgaudit to monitor only writes on any table. Test your configuration works and check the contents of the logfile.

## Trigger-Based Auditing

Use cURL to download the generic trigger-based auditing script from https://raw.githubusercontent.com/2ndQuadrant/audit-trigger/master/audit.sql. Execute the script on your Pagila database.

This script does the following:

-  Creates a table to hold the audit data (this table is place in its own schema for security)
-  Provides a function audit.audit\_table(), which creates audit triggers on the chosen table
-  Creates a view audit.tableslist which shows all tables are subject to trigger-based auditing

## Enabling the hstore Extension

The audit script uses a postgres extension called hstore . This extension allows you to pass in JSONlike data to the database. This is not compiled by default. In order to make the script work you will need to compile and install it. The hstore extension is pre-built with PostgreSQL 14. Simply run: CREATE EXTENSION hstore; No compilation required.

## The audit\_table() function

The audit\_table() function is available in the audit schema. In order to use this function you need to use a SELECT query, giving the function name (fully-qualified i.e. audit.audit\_table(&lt;param1&gt;, &lt;param2&gt;, &lt;param3&gt;) ). You need to supply the values for the parameters when you call the function (don't include the angle brackets. The audit\_table function takes the following parameters

-  target\_table: the table name (including schema)
-  audit\_rows: whether to audit changes to each row, or just at the statement level ('t' or 'f')
-  audit\_query\_text: whether to include the SQL query in the audit
-  ignored\_cols: array of columns to ignore, ARRRAY['column1', 'column2', 'column3']

## Set up Auditing

After running the script, use the audit\_table function to set up the following audits

1. customer table: audit all rows, include query text
2. actor table: audit all rows, do not include query text
3. language table: audit at statement level, include query text

Insert, update and delete a row from each of these tables. Check the audit table to make sure the audit works as expected.