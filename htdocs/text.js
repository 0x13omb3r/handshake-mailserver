

function welcome_text()
{
	return `<table align=center width=75%><tr><Th><h2>Welcome</h2></th></tr>
		<tr><td><div style='height: 20px;'></div></td></tr>
		<tr><td style='white-space: normal'>
		Welcome to a Handshake-aware WebMail Service. Using this service you can send and receive emails between email addresses in any Handshake Domain.
		You can also send email to ICANN domains, if their SMTP Server uses an Handshake-aware DNS resolver.
		<div style='height: 20px;'></div>
		To use this service, you must
		<li> Own a Handshake Domain and be able to configure it's DNS
		<li> Register to use the domain on this site
		<li> Add a DNS MX record we give you to  prove you own the domain and direct your email to this service
		<P>
		<div style='height: 20px;'></div>
		You will be able to read your email through this website, by SSL-IMAP or SSL-POP3.
		You can send mail to other members of this site using SMTP, but you will only be able to send mail externally (to ICANN or Handshake domains) using the webmail interface. This is to discourage spammers/scammers.
		<P>
		If you use IMAP, and store your mail folders on the site, I strongly recommend <a target=_blank href='https://www.google.com/search?q=backup+imap+folders+tool'>you arrange to back them up</a>. We offer no guarantees, beyond 'best effort'.
		<div style='height: 20px;'></div>
		To get started, click <b>Register</b> above!
		<P>
		<a href=# onClick="show_more_help(); return false;">More help available here.</a>
		</td></tr></table>`;
}

function show_more_help()
{
	elm.default.innerHTML = user_help();
}


function user_help()
{
	return `
<table align=centre border=1 width=75%><tr><td style="white-space: normal">
<h1>User Help</h1>

<h2>Getting Started</h2>
Before you start you will need to own a Handshake Domain. This can be any kind of Handshake domain, so top-level-domains, second-level-domains or even third/forth level domains are fine, including emoji/emoticon domains. The only requirement is you are able to set a DNS MX record in the domain.<P>
To get started, register an account using a Handshake domain. It will ask for your domain name and a password. You will use this password to access both the registration interface and your email/webmail.<P>
It will ask for an email address to use for password resets. If you don't want this, just enter garbage that looks like an email address, but this site will NEVER send emails to this address, except as part of a password reset process.<P>
If you are using an emoji/emoticon domain and want to make certain the correct domain name is registered, we recommend you register using the Puny Code, but you can register / login using the Unicode if you want.<P>

<h2>Proving You Own the Domain</h2>
Once you have registered, you will be given an MX code to put into the apex of your domain. This does three things.<P>
<li>1. It proves you own the domain
<li>2. It directs the email for that domain to this site
<li>3. Helps us get your mail into your mailbox
The MX code will look something like this â€œqq2pqslz7wfq7qjwedrfedwsqaj63zh2q4cmt23k45rf7y4wfch4.shakethemail.netâ€.<P>
In DNS, MX records also require a â€œpriorityâ€ number. You can just use â€œ10â€. Depending on your DNS provider, this may be a prefix to the MX name, or may be entered as a separate field.<P>

Once you have set the MX code in your domain, it can take this site up to 24 hrs to see this change. This is a common feature of DNS.<P>
After the system has seen the MX code in the domain, it will activate your account. This will mean you now have full access to the email service.<P>
If you do not activate your account within 7 days, the account will be automatically deleted.<P>
If you log into the registration site, you can click the â€œDomainsâ€ button to see the activation status.<P>
On Activation, you will have one default email address, <your-domain>@shakethemail.net. To add email addresses in your own domain, you will need to log into the webmail interface, at https://ShakeTheMail.net/webmail/<P>
In the WebMail (provided by Rainloop), go to Settings->Accounts and click the â€œAdd an Identityâ€ button. You can create as many email addresses in your domain as you like. Sending will fail if you try adding email addresses in domains you have not proved you own.<P>
New identities will show up immediately in the â€œDomainsâ€ page of the registration site.<P>

<h2>Adding Other Domains to Your Account</h2>
If you wish to add more domains to the same account, you can simply add email addresses ending in the new domain name and you will see them immediately show up in the â€œDomainsâ€ page of the registration site.<P>
You will then need to add the exact same MX code to the new domain to prove your ownership. Each account has it's own unique MX code.<P>
<b>Top Tip:</b> If you add the MX code to the domain before adding email identities in that domain, then the domain will usually activate much faster, often immediately.<P>

<h2>Adding More Accounts</h2>
If you have additional domains, but you want to keep the email separate, you can  register them separately at the registration site. <P>
Each registration will have a unique MX code and a separate set of mail folders (INBOX etc).<P>
However, Rainloop allows you to control multiple accounts from a single login. To do this, log into Rainloop with the account you want to use as the primary account, then go to Setting->Account and click â€œAdd an Accountâ€ to add an account as a secondary account.<P>
You will then log into Rainloop using the primary account, but can then switch to the secondary account without having to log in again.<P>

<h2>Accessing Your Email</h2>
You can access your email directly at the site using the Rainloop webmail interface provided, or you can use any standard email client.<P>
The site supports SSL/IMAP, SSL/POP3 and SSL/SMTP. The webmail interface allows you to send mail to any email address, but the SSL/SMTP only lets you send mail to other members of this site. This is to try and deter spammers/scammers.<P>
Your login to the POP3/IMAP services is the domain name you used to create the account. You can not login using any domains you added to the same account later.<P>
This site makes no warrantee on retaining your email beyond â€œbest effortsâ€. Therefore, if you chose to store folders on this site(e.g. IMAP or WebMail), we STRONGLY recommend you make suitable arrangements to make backup copies. Various IMAP backup tools are available.<P>
If you want to keep your email more private, we recommend you collect the mail off the site, using POP3 â€“ or you can simply run a copy of this service yourself.<P>

	</td></tr></table>
		`;
}

