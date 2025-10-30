# NFC Tag Authentication Explained - Seritag

****

*9 pages*

---

## Page 1

STORE
 
BUYING ADVICE ▾
 
LEARN
 
Q&A
 
NEWS
 
CONTACT
 
£ ▾
SERITAG
BASKET
 /   Learn /   Using NFC /   NFC Tag Authentication Explained
NFC Tag Authentication Explained
03 JANUARY 2020 (UPDATED: 25 JUNE 2024)  |   USING NFC
NFC tags have a wide and growing number of uses. However, to an extent,
NFC has always been an 'optional' technology rather than an 'essential'
technology. For example, if you are an advertising agency and are looking to
create a link between your physical packaging and your website - you might
consider NFC, but you'll also consider QR codes. This isn't the article to go
into the pros and cons, but the point is that you have options.
Recently however, there's a new generation of authentication NFC tags
arriving on the market. Seritag consider these to be an important
development to the NFC tag authentication landscape.
The ability to add an NFC tag into a product to allow authentication with just
a mobile phone by any user, anywhere. That's powerful.
Search..
What is an NFC Tag ?
A quick intro to NFC
tags - what they are,
how they are used and
the different types of
tags
Options price list
Pricing for our
encoding, scanning, ID
printing and batching
services.
NFC Tag encoding
Details of our NFC tag
encoding services.
ID printing
How to order ID / QR
code printing on your
NFC tags.
UID scan
How you can order a
UID scan of your NFC
tags.
Latest Articles


---

## Page 2

Authentication vs. identification
To make things clear, let's define the difference between identification and
authentication. We will use the example of an NFC tag being attached to,
say, a handbag.
Identification is the ability of the tag to identify that particular model of
handbag. It might provide information about the supply chain, the store that
sold it, perhaps even the previous owners. It might provide specific
information on that exact handbag. However, there's no guarantee that the
tag, and therefore the handbag is actually genuine or the handbag the user
thinks it is.
Authentication tags take that extra step. They allow the user to not only
identify the handbag but also provide a very high level of security that the tag
(and therefore the bag that the tag is attached to) is in fact the item it claims
to be.
However, authentication isn't just about preventing counterfeit products, it
can also be used for access control, user authentication, connecting to an
NFT and the metaverse, ticketing, gaming, document authenticity and much
more.
How do NFC authentication tags work ?
In a nutshell, they prevent cloning by generating a new unique code on each
scan which can be verified by a third party server.
While a standard NFC tag can be used to identify a product or item, there's
nothing (generally) to prevent it from being duplicated into hundreds of
counterfeit products. An authentication tag cannot be copied so each
product has a substantially increased level of counterfeit protection.
Old school vs. new school authentication tags
Using authentication in NFC tags isn't exactly new. It's been used for
ticketing and access control for years. So what's different ? The difference is
the way that the data is presented and how that will be used.
Seritag News
New NFC
Cable Tie and
NFC
Wristband
Starter Packs
New cable tie and
wristband starter
packs
Industry News
Seritag launch
Lumiio -
instant access
to essential
personal
information
Seritag launch
Lumiio for
essential personal
info
Seritag News
How long do
NFC products
really last
outdoors? We
put them to
the test!
To find out how
well our products
hold up over time,
we left them
outside our UK
office for three
years in all kinds
of weather.
Discover which
ones stayed
strong, which
ones didn’t, and
what we’re te
Using NFC
Using NFC
Tags in
Churches for
Donations and
Interaction
Discover how
churches are
using NFC
technology to
increase
donations, interact
with the younger
generation and


---

## Page 3

To keep things simple, in the old school chips, the authentication stuff was
embedded deep within the chip. You needed special NFC commands to
access and control authentication. With some chips, you could, in theory, do
this with an App on Android phones but it was complicated and not easy to
implement.
Some of the newer generation of NFC tags also have system to check the
authenticity of the chip manufacturer, which is linked to the UID of the chip.
However, this is a 'static' signature and while more difficult to clone, its not
widely accepted to be a 'good solution'.
The new generation of chips have two benefits.
First, they generate a unique code on each scan which means that any data
copied is incorrect on the next scan.
Second, they can present the data within the URL NDEF area of the tag. In
short, this means that all you need to do is scan the tag with a regular NFC
phone without any App and you can use the authentication tech. This is
called 'frictionless' - you can just tap and go.
Who is making these chips and tags ?
There are a few authentication chips on the market already although the
options are changing quickly. The most popular are NXP's NTAG424 DNA,
NTAG426Q, NTAG223 and NTAG224, EM's EM|Linq and HID's Trusted
Tag. However, these are the chips - not the finished tags.
There are a large number of authentication tags available and we sell
thousands of these every day. However, these chips are slightly more
expensive than regular NTAG213 chips.
Seritag have a large number of NTAG424 products in stock, available for
immediate dispatch. If you are wanting to encode these tags for
authentication purposes, please get in contact with us as these tags require
specialist encoding and key management - something that very few
companies can do.
The NFC authentication process explained
interact with their
community.
Industry News
How will
adding RAIN
RFID to mobile
phones impact
the market ?
A discussion on
RAIN UHF in
mobile devices
Using NFC
Seritag
Encoder App
Learn the key
features of our
new Seritag
Encoder App.
Encode, read and
lock NFC tags
yourself using
your mobile phone
for free!


---

## Page 4

There are variants of the NFC tag authentication process but the principle is
similar. Each tag is encoded with a special key that cannot be seen. That key
is used to generate a unique code on each scan which can be added to the
standard NDEF data. This means, for example, the unique code can be
automatically added to a web address encoded on the tag with each scan.
That unique code can then be checked on a remote server using a copy of
the same key. The result is that the authenticity of the tag can be confirmed.
If the unique code was not what was expected, then the tag can be assumed
to be a copy. Each code can only be used once. Once the code has been
verified on the server it is no longer valid.
NFC Tag Authentication Procedure
▶


---

## Page 5

To explain in very simple terms how the key system works, let's consider a
simple four digit key - 8774. This key is held and hidden on both the tag and
the server. On the server, we will also associate this key with a specific tag -
in this case tag '123'.
When the NFC tag is scanned, the NFC chip within the NFC tag performs an
encryption calculation based on two elements - the scan count (how many
times the tag has been scanned) and the key.
So in the example above, the tag will use the key (8774) and the scan count
(3) to generate a unique code using an encryption algorithm. In our example,
we've generated the code a43f3.
This code (a43f3) is then dynamically added to the web link encoded on the
tag along with the scan count (3) and the id number of the tag (123).
The unique code is dynamically added to the URL encoded on the tag each
time the tag is scanned. To allow this, when the tag is encoded, we leave a
'space' on the URL for the chip to dynamically fill that space with the unique
code.
That web link is now used to load the web page on the phone. The web page
will come from remote web server. The remove server then reads the unique
code, the scan count and the tag ID by taking the parameters (data) passed
to it in the URL.
Then, the server either checks that code itself or (behind the scenes) asks
another authentication server if that code is valid.
The authentication server uses the count and the same hidden key (8774) to
also generates the unique code (a43f3). In doing so, it can check that the
code provided by the tag is indeed the same as it would have expected. The
authentication server will typically use the tag ID which was also supplied to
use the correct hidden key as in most cases each tag will have it's own key.
Now, depending on whether the codes match or not, the web page can
dynamically serve the appropriate content back to the user.
The important point here is that during this process, the keys are not stored
or required by the mobile phone. They are not visible to the person scanning
the NFC tag at any stage.


---

## Page 6

Using NFC authentication tags with an App
In the example above we illustrated how an authentication tag can be used
without any App installed on the phone. The tag scan will launch a web page
from a remote server.
The same authentication tags can also work in an App environment. The
keys are still stored on the tag and remote authentication server in the same
way but the App in the middle handles the auth check.
Using an App to scan an NFC authentication tag
 
Depending on the phone/setup the user will either open the App and scan
the tag or just scan the tag to launch the App (step 1 and 2).
Once the App is open and tag scanned, the App can perform a check behind
the scenes against a third party server by passing the auth server the tag ID,
count and code scanned from the tag (step 3).
The auth server then responds with the validation (step 4) and the App can
confirm whether the item is genuine or fake (step 5).
Again, as with the frictionless web based version, the security keys are not
stored in the App itself and are never seen or transferred during this process.


---

## Page 7

It's quite possible to use the same tags for both a web scenario and App
scenario. In this case, the tags can be scanned without an App and they will
launch a web page. If the App is opened first before scanning the tag, the
same data can be accessed and then managed via the App.
For reasons we'll cover later, using an App can provide an increased level of
security. However, allowing customers to do both is flexible and powerful
option.
Tag authentication keys
The actual size and definition of the keys depends on the chip manufacturer.
However, typically, a key will be a random sequence of 16 characters.
Ideally, each individual tag would be encoded with it's own unique key. The
server then stores which key is associated with each tag ID. During the
encoding process of putting the data onto the tag, the tag ID is also stored
so that it's visible during the tag scan.
The authentication server then requires three bits of information - the tag ID,
the scan count and the unique code.
The management of these keys is important as if the keys are not held
secure then the security of the tags will be compromised. It would be
possible with access to the keys to create replicas of the tags themselves
and therefore create counterfeits.
It's worth mentioning at this point that the process of encoding NFC
authentication tags is substantially more complicated than encoding a
normal tag. It goes without saying that any incorrect encoding can make the
use of authentication tags worthless.
How secure are NFC authentication tags ?
The simple answer is that they are as secure as the little keypads that are
often used to access bank accounts. The real risk is far less in the tags
themselves but flaws in the ways that they are used or encoded.
Can the encryption and the keys be hacked ? Quite possibly but in reality it's
not easy and ultimately, in most use cases, it's more than strong enough.


---

## Page 8

So where are the flaws ? The first is inherent with 'frictionless' tag scanning.
Essentially, the principle is that the tags can be scanned by any NFC mobile
without an App. The tags, when scanned, will direct through to a website.
The uniquely generated code is automatically embedded in the URL which
the phone uses to collect the webpage and the server checks the code
behind the scenes to say whether the tag is authentic or not. The flaw is that
most users don't know what web page they are going to see.
For example, a luxury brand may place an authentication NFC tag in a
handbag. User scans the tag and gets redirected to the luxury brand's
website which says whether it's authentic or not. However, the user doesn't
know what that web page looks like because they've never seen it before. So,
a company making fake handbags can simply add any NFC tag redirecting to
any webpage anywhere saying it's not fake. User doesn't really know the
difference.
Now, this is only going to be a problem where general users don't know
which page they are expecting to see. In closed loop systems such as a
supply chain, the person doing the scanning might know what to expect and
be ready for something that looks odd.
The solution to this is using the authentication tags with an App. The user
downloads an App first before scanning the tag and thus the system is
substantially more secure. The App can control the connection to the auth
server and check any incorrect information on the tag.
Is this a problem ? Probably not. In many consumer driven cases, the whole
purpose of authentication tags in, for example, luxury goods is more to do
with consumer interaction than any real control over counterfeit products. In
which case, the act of authenticating the goods gives a reason to download
the App and goal is achieved.
In other cases, such as the individual tagging of documents or other such
items, it's more the ability to hybrid identification with a simple frictionless
security element quickly and easily.
Using Ixkio & Seritag for NFC authentication
We have been testing and working with almost all the authentication tags on
the market for many years. As a result, we are very aware of the power of
these tags but also how important it is to use them correctly.


---

## Page 9

Seritag currently offer two options to allow our customers to use
authentication tags :
We can supply the tags themselves using either NXP's popular NTAG424,
NTAG223, NTAG224 or EM's EM|Linq chips so that customers can encode
and develop solutions themselves. We now stock a wide selection of
NTAG424 products including garment tags, disc tags and PVC cards. We can
also supply a range of NTAG424 custom printed products including custom
print labels and cards.  
If you aren't sure which product you might need and want to see
authentication tags in action, then we now also supply an Authentication
NFC Tag Starter Pack which can be purchased online. 
For customers that don't want to develop full systems, we can provide an
encoding service integrated with our Ixkio tag management platform. Tags
can either be encoded to redirect through the ixkio system or can be
encoded to direct to customer website/pages. The ixkio platform can then
either check authentication on the redirect or via an API request. 
It's important to understand that while these tags are very powerful and
encoding/authentication the tags is complicated, using them is actually very
easy. We can handle the supply, provision and authentication process - you
simply need to add them to your product.
Customer Information
FAQ
Refunds
Delivery
NFC Tutorials
News & Blog
NFC Applications
Ixkio Tag Management
Lumiio
vCard-Go
Seritag
About us
Contact
Privacy
Terms
5.0
1,806
reviews
Contact
Email: mail@seritag.com
Tel: + 44 (0) 20 3773
2791
 
©Copyright 2025 Seritag.
Seritag is a trading name of TabDesk Ltd, a UK Registered company 10474154. VAT Registration Number GB256328005.


---
