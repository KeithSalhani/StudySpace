## INSTALLING POSTGRESQL SNDBA Lab 1

<!-- image -->

## Aims of the Lab

In this lab we will

-  Install Ubuntu Linux in a VirtualBox environment
-  Build and Install PostgreSQL from source
-  Configure the database and connect from within the guest machine

While working through this lab, you will need to keep a couple of screenshots for your lab submission. These can be copy/pasted into a word document.

## 1. VirtualBox

- 1.1 Download and install the latest version of VirtualBox for your platform https://www.virtualbox.org/wiki/Downloads
- 1.2 For quality of life ( e.g. the ability to copy and paste between host and guest) I recommend installing the Linux Guest Additions (see chapter 4.2.2.1 of https://www.virtualbox.org/manual/ch04.html)
- 1.3 Determine how much disk space is required for a Postgres installation (see chapter 17 of the docs)
- 1.4 Determine how much disk space is required for Ubuntu Server (again, see the docs)
- 1.3 Open VirtualBox and create a new Virtual Machine.
-  For maximum performance, allocate 50% of available RAM
-  Choose a Virtual Disk Size large enough to cover your requirements

## 2. Installing the OS

We'll be using Ubuntu 22.0.4 server; the latest Long Term Services (LTS) release.

- 2.1 Download Ubuntu 22.0.4 server Ubuntu website
- 2.2 Start the newly created virtual machine
- 2.3 You have the option to 'insert the .iso' available in the Devices menu of VirtualBox
- 2.4 Run the installer, making sure to install OpenSSL

## 3. Installing PostgreSQL Overview

For the remainder of the lab, we will compile and install PostgreSQL from source. The general process is

1. Download the source
2. Make sure we have the required dependencies installed (make configure)
3. Compile the source code into executable files (make)
4. Move the executable files to the correct location on our machine (make install)

The general walkthrough can be found at https://www.postgresql.org/docs/16/index.html .

Installing software such as this is a big part of any administrator's job and requires reading and forethought to do correctly. Whenever taking on a big installation project like this you should

-  Read through the steps in the docs fully (make sure everything makes sense)
-  Return and work through each step one-by-one (make sure you get the expected output at every step)

Ignore section 17.1 (short version), this is a cheat-sheet to help people remember the overall steps; unless you know exactly what you're doing, many of the commands won't work and you'll end up having to undo anything you do here.

Start with section 17.2 of the docs and make sure you have the required software available.  Continue with 17.3 to download and unpack the source files, and

## Notes to Section 17.2

You can test whether a programme is available using the which command. which takes command takes a command and checks all of the directories in your path. It returns the location of the supplied command (or nothing if the command is not found). To check if the application curl is installed, for example, we can use &gt; which curl

The readline and zlib libraries are mentioned in the requirements. As libraries, rather than commands, these can't be located using which, but we'll be prompted to install these libraries late when we configure our installation so it's safe to ignore for now.

The only optional package we require is openssl, which should have been installed earlier (check this using which).

## Notes to Section 17.3

This section assumes you have the source code on your machine. You will need to download it first (there's a link in this section to the source downloads). The curl command allows you to download a file from a URL. By default, curl displays the contents of a webpage on the terminal. Make sure you use the -O option (that's capital o) to tell it to save the output to a file instead It's good practice to check the md5sums to make sure the file downloaded correctly. Each file on the downloads page has an equivalent ending in the .md5 extension. This is simply a text file showing you the expected output of running that file through the md5sums command. Try it out and make sure they match.

## Notes to Section 17.4

Make sure you've cd'd into the unzipped source code before you begin this section By default, the terminal doesn't let you scroll, you can finish any command with | less (vertical bar piping the output to the less command) to allow yourself to scroll.

The output of configure will complain if the readline library isn't installed but won't be very helpful on how to install it. The packages you need to fix this are lib32readline8 , lib32readline-dev and libreadlinedev Similarly, for the zlib library the required package on Ubuntu is zlib 1 g-dev (the character in bold is the number one). Make sure you run the ./configure script with the -with-openssl option. The package you need to install to allow this is libssl-dev Very often Linux documentation doesn't specify when you need admin permissions to perform a particular operation. This is because some distributions allow you to operate as the root user. If you get an error saying permission denied or cannot create regular file , odds are you need admin permission; re-run the command with sudo to fix the issue.

## Downloading the Source Code

- 3.1 Our first step is to download the source code for PostgreSQL. Create a downloads directory using the mkdir command and cd into the directory.
- 3.2 You can use curl to download files from the internet. By default, curl will print the contents of a webpage to the console, to force it save the file use the -O flag. You can use man curl to get information on how to use the command. The source code is available at https://www.postgresql.org/ftp/source/
4. Unpacking the Source Code

Full walkthrough available on the postgres docs. We can tell from the file extension (.bz2) that the postgresql source code has been compressed using BZip. Our first step is to unpack it using the tar command. The following options are used x: Tells tar that we want to e x tract files from the archive v: Tells tar to display verbose output j: Tells tar that this archive is compressed using bzip2

- f: Tells tar that the next part of the command is the filename to extract
- 4.1 Unzip the file using the command tar -xvjf &lt;filename.tar.bz2&gt;
- 4.2 Check that the folder has been created and cd into it. Use ls to check the contents of the folder.
- 4.3 You should see a file called configure, this is an executable script which will prepare the software for installation. We can run it from the command line (don't forget the ./ at the beginning)
- ./configure

Check the output, you will most likely get an error telling you that no c compiler was found. Let's fix that.

- 4.4 We can use the gcc compiler to build postgresql. The gcc compiler is available from the apt repositories
- sudo apt install gcc

While we're at it, there are a few more packages which need to be installed. You will get an error from the configure scripts if they are missing, but here's the list you need. Install them using apt libreadline6-dev, zlib1g-dev, make After the configure script has run successfully, you will see that a file called Makefile has been created. We can use this file to continue the installation. The make command allows you to easily compile software using a makefile. Any make command must be issued in the directory containing the make file.

- 4.5 Make sure you're in the directory containing the makeFile and issue the command, make

The make command will take a while to run. While you're waiting, check out the documentation and find out what flag you could pass to the configure command to compile your database to allow Python code to run on it. Once the database is installed, we want to make sure it runs OK on the system. The make check command will run a suite of automated tests to ensure everything went well

- 4.6 Run the regression tests using make check

Finally, we use make install which will copy the created files to their permanent home on your machine (in our case we've specified /usr/local) .

You'll need to use the sudo command to run this as root as only the super user has permissions on these directories.

- 4.7 Install the files using sudo make install

## 5. Post-Installation

The post-installation steps tell you to add postgres to your path. The commands to do this are given to you in the docs. The docs suggest adding this to your .bash\_profile config file. Now that postgres has been installed we need to create a user to run the software. Use the adduser command to create this account 5.1 sudo adduser postgres We'll also need a folder which the database can use to store all of its data 5.2 sudo mkdir /usr/local/pgsql/data Grant ownership of the folder to the postgres user 5.3 sudo chown postgres:postgres /usr/local/pgsql/data Next we need to switch to the postgres user and initialise the data folder. The D flag tells the database initialisation script which directory to use to store the data.

- 5.4 sudo su postgres

## Modifying the postgres user's Path

All of the PgSQL executables are located in the /usr/local/pgsql/bin/ directory. You can make life easier for yourself by adding this directory to your PATH. This will mean you won't have to type the full path every time. In order to do this, switch to the postgres user, cd into their home directory and open the .bashrc file for editing (use nano or your favourite text editor). Add the following line to the top of the file. export PATH='/usr/local/pgsql/bin:$PATH' source .bashrc

- 5.5 initdb -D /usr/local/pgsql/data/

Check that the data directory has been populated using the ls command before continuing. Once we're happy that the data directory has been initialized, we can start the server. The server programme in postgres was called postmaster . Now it's simply postgres. So, if you are using an older version, use postmaster instead of postgres. We need to specify the data directory when starting the server.

We also need to include an &amp; sign at the to run the server in the background. 5.6 postgres -D /usr/local/pgsql/data &amp; Now that the server is running, we can create a test database using the pgsql createDatabase command. This command will create a database named &lt;dbName&gt; (don't include the &lt;angle brackets&gt;). Create a database using your student number as its name 5.7 createdb &lt;dbname&gt; Finally, we can connect to the database using the psql client. 5.8 psql &lt;dbname&gt; Issue a query to make sure everything works as expected. You can get a list of tables in the database by selecting from INFORMATION\_SCHEMA.TABLES. 5.9 SELECT * FROM INFORMATION\_SCHEMA.TABLES

## Submission

cd in the /usr/local/pgsql/data directory and run the ls screenshot of the output as your submission for Lab 1.

command. Add a

You will demo your working database installation in the lab next week.

## Review

In this lab we downloaded and compiled a postgresql database from source We created a separate user to run the database to ensure proper security practices are followed We configured a data directory and created a test database