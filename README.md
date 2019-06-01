# shoes-feed

Feed data gathering on flea markets for shoes.

### stockx

##### stockxapi

https://pypi.org/project/stockx-py-sdk/

Customizations
* Requests user-agent header to evade bot check
* Orders serialization
* Order type typo correction

##### what to expect

* Query output ('air jordan')
```
name Jordan 1 Retro High SP Gina
  best bid 2000
  best ask 242
  last sale 236
  sales last 72 116

name Jordan 7 Retro Ray Allen Bucks
  best bid 185
  best ask 185
  last sale 189
  sales last 72 159
```

* Book builder (per `<shoe model, size>` of given product ID):
```
---- adidas EQT Support 93/17 Core Black Turbo : 9.5 ----
---- Bid ----  ---- Ask ----
               260.00 1
               258.24 1
               258.00 1
     1 170.00
     1 167.00
     1 165.00
     1 120.00
----------------------------
Spread: 88.00. Mid: 214.00

---- adidas EQT Support 93/17 Core Black Turbo : 10.5 ----
---- Bid ----  ---- Ask ----
               221.16 1
               194.00 2
     1 135.00
     1 56.00
----------------------------
Spread: 59.00. Mid: 164.50
```

### flightclub

### ebay

### amazon


