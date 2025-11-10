# Handshake Mail Server
This repo contains the code to make a container to run a Handshake Mail service, including WebMail (Rainloop), SSL/POP3, SSL/IMAP and SSL/SMTP.

NOTE: the SSL/SMTP only allows you to send mail to other members of the same site, but you can send mail to external addresses (both ICANN and Handshake) using the Webmail interface.

You can only send email to an ICANN destination where their mail server uses a Handshake aware resolver, but this is normally the only requirement for them to send & receive email with Handshake.

If you don't want to build the container yourself, it is available on [docker.com](https://docker.com) at `jamesstevens/handshake-mailserver` (https://hub.docker.com/r/jamesstevens/handshake-mailserver).

There is a free public Handshake email service, using this container, at [https://ShakeTheMail.net/](https://ShakeTheMail.net/).

## Running this Container
All you need for running this container is a server running docker & some disk space. You will also need to know the IP Address(es) of an open dns resolver that support Handshake.

The basic procedure is, run the container once, customise the default configuration then restart it and you're ready to go.

When you get docker to run the container you will need to map your disk space to the container's directory “/opt/data” and you will need to use the docker option `--dns` to specify which Handshake-aware DNS servers you want it to use.

It is also common for mail servers to like to see the hostname and IP Address mail is sent from match each other. They also like the reverse DNS on the IP Address to match the host name. You can use the docket option `--hostname <name>` to specify the host name within the container.

## SSL Security
When running the container, you can either get the container to handle the SSL, or you can do it externally, e.g. using `nginx`, `haproxy` etc.

If you do it internally, you will need to copy a PEM file into `{{DATA}}/pems/server.pem` - the file must contain both the private key PEM and the certificate PEM. The container will look for this file getting updated and will automatically install the new certificate and tell the internal software to update.

If you run the SSL externally, I recommend you proxy the following ports


| Public Facing Port | Use | Container's Port
|---|---|---|
| 993 | IMAP | 143
| 995 | POP3 | 110
| 465 | SMTP | 25
| 443 | HTTP | 80

If you are using the container to handle the SSL, then you will need to map the "Public Facing Ports" into the container.
If you are handling the SSL externally, then you will need to map the "Conainter's Ports" into the container.

You may also want to map port 587 into the container. Even if you are handing the SSL externally, you
should map port 25 into the container for the benefit of older SMTP servers.

If you do not provide a `server.pem` file, the system will make one using an ephemeral private certificate authority, using the information attributes in the `policy.json` file (see below).


## Custom Configuration
After you have run the container once, it should have created the file `{{DATA}}/service/config/policy.json` - it will container the system default values.

You will definitely need to change `email_domain` and `website_domain` to match the domain you plan to use for your site. You will also probably want to change `website_title`, which is the title on the web pages.

You may wish to change `manager_account` which is the name of the site manager's account – the default is `manager`. This can be harder to change once the site has been up and running a while.

All the items that start “cert_site_” are only for creating the private certificate described above.

The item `allow_icann_domains` is a boolean (true/false) that says whether users can register on the site using an ICANN domain name. By default is this `false`, which means the site will only support registration of Handshake domain names.

NOTE: the items `website_title`, `email_domain` and `manager_account` are merged into the Webmail (Rainloop) base configuration. If you make changes to the Rainloop configuration by hand, the system will no longer merge these changed into the Rainloop configuration, so you would need to update them by hand.

Once you have edited the `policy.json` file, restart the container and you are ready to go.

## The System “Manager”
The account for the person who manages the system is “manager”, by default. If you wish to change this I STRONGLY recommend you do it at the very beginning. The default password is “12345”, I even more strongly, recommend you change this.

The manager has three access points, the registration site, their email account and the interface for customising the webmail interface.
When the system sends emails to the users, they will always come from the "manager" account.

The password for the registration site and the mailbox are managed together, but the password for customising the webmail interface is manager separately in Rainloop. This means you will need to change the password in two places – the registration interface and the Rainloop Admin interface.

When the manager logs into the registration site, they should not only get the “Webmail” button like normal users do, but an additional button labelled “Mail Admin” which takes them to the Rainloop Admin interface.

## Example Run Script

		exec docker run \
				--read-only \
				--hostname mail.shakethemail.net \
				--dns 192.168.8.110 \
				-v /opt/data/handshake-mailserver/:/opt/data \
				-p ${ip_pb}:993:993 -p ${ip_pb}:995:995 \
				-p ${ip_pb}:25:25 -p ${ip_pb}:465:465 -p ${ip_pb}:587:587 \
				-p ${ip_pb}:80:80 \
				-it handshake-mailserver

In this example, I have disk space on the container host at `/opt/data/handshake-mailserver`, so I am mapping
this into the container for it to use as storage.

NOTE: this container is designed to run read-only. This improves security, so I recommend you also use this option.

`${ip_pb}` is a variable that holds the container host's IP Address I am using for this container.

## Customising the Build
If you wish to customise the build, the text of the welcome & help page is held in the file [htdocs/text.js](htdocs/text.js)
making it easy to replace this text with whatever you want.

All the default email templates are copied into `{{DATA}}/service/emails/*.eml`, so you can edit / replace them there.
The common header & footer are `start.inc` & `end.inc` respectively.
