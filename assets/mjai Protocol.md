# Mjai Protocol

From: https://mjai.app/docs/mjai-protocol

Our Mjai protocol is largely based on Gimite's original Mjai protocol, with a few minor changes. The majority of the implementation is based on Mortal's libriichi. Some rules have been added, such as the rule that players pay a penalty when they make an runtime error.

## Overview

First, 4 players listen for connections as TCP servers. Then, the game simulator sends JSON event messages to the players until the game end.

## Tile format

In addition to the 34 basic tile types, there are three types of red dora and unseen tile representations.

Manzu (萬子): "1m", "2m", ..., "9m"
Pinzu (筒子): "1p", "2p", ..., "9p"
Souzu (索子): "1s", "2s", ..., "9s"
Wind (風牌; Kazehai): "E" (東; Ton), "S" (南; Nan), "W" (西; Shaa), "N" (北; Pei)
Dragon (三元牌; Sangenpai): "P" (白; Haku), "F" (發; Hatsu), "C" (中; Chun)
Red doragon (赤ドラ; Akadora): "5mr", "5pr", "5sr"
Unseen tile: "?"

### Example JSON events

The player receives a list of JSON event messages up to the next actionable event.
Below is example JSON messages. "<-" represents a message from the game simulator. "->" represents a message from a player.

Line breaks
For readability, line breaks have been added in the messages. The output of the simulator does not include line breaks.

```
<- [{"type":"start_game","id":0}]
-> {"type":"none"}
<- [{"type":"start_kyoku",,"bakaze":"E","dora_marker":"2s",
"kyoku":1,"honba":0,"kyotaku":0,"oya":0,
"scores":[25000,25000,25000,25000],
"tehais":[
["9p","7m","9s","9s","8m","5s","2p","W","C","5s","N","5mr","F"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"]
]},{"type":"tsumo","actor":0,"pai":"6p"}]
-> {"type":"dahai","actor":0,"pai":"W","tsumogiri":false}
```

## Flowchart

The following flowchart shows the order of JSON events to be handled.
![flowchart](https://mjai.app/flowchart.png)

## Events

### Start Game

id represents the seat number in the game. 0 represents the chiicha (起家; first dealer),1 the shimocha (下家; player to the right) of the chiicha, 2 the toimen (対面; player across) of the chiicha, 3 the kamicha (上家; player to the left) of the chiicha.

The player always returns a "none" event.

```
<- [{"type":"start_game","id":0}]
-> {"type":"none"}
```

### Start Kyoku

The hand tiles (tehais) and scores are arranged in the order of the id in the start_gameevent.

Since start_kyoku events are not actionable, you will not receive only a start_kyoku event.

```
<- [{"type":"start_kyoku",,"bakaze":"E","dora_marker":"2s",
"kyoku":1,"honba":0,"kyotaku":0,"oya":0,
"scores":[25000,25000,25000,25000],
"tehais":[
["9p","7m","9s","9s","8m","5s","2p","W","C","5s","N","5mr","F"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"]
]},{"type":"tsumo","actor":0,"pai":"6p"}]
-> {"type":"dahai","actor":0,"pai":"W","tsumogiri":false}
```

### Tsumo & Dahai

In a single kyoku (局; round), the "tsumo" event is one of the most common events.

If the "actor" attribute of the JSON data matches the player's ID, the "tsumo" event becomes an actionable event. According to the rules of the mahjong game, some of the following events can be output as a response:

```
<- [{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"7s","tsumogiri":false},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"F","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"2m","tsumogiri":false},
{"type":"tsumo","actor":0,"pai":"3m"}]
-> {"type":"dahai","actor":0,"pai":"3m","tsumogiri":true}
```

### Call: Pon

```
<- [{"type":"dahai","actor":1,"pai":"5sr","tsumogiri":false}]
-> {"type":"pon","actor":0,"target":1,"pai":"5sr","consumed":["5s","5s"]}
<- [{"type":"pon","actor":0,"target":1,"pai":"5sr","consumed":["5s","5s"]}]
-> {"type":"dahai","actor":0,"pai":"9p","tsumogiri":false}
```

### Call: Chi

```
<- [{"type":"dahai","actor":3,"pai":"4p","tsumogiri":true}]
-> {"type":"chi","actor":0,"target":3,"pai":"4p","consumed":["5p","6p"]}
<- [{"type":"chi","actor":0,"target":3,"pai":"4p","consumed":["5p","6p"]}]
-> {"type":"dahai","actor":0,"pai":"9m","tsumogiri":false}
```

### Call: Kakan

In the case of Kakan (加槓 pon + 1 from self), the next dahai event is followed by a dora event.

```
<- [{"type":"tsumo","actor":0,"pai":"9p","tsumogiri":false},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"7s","tsumogiri":false},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"F","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"2m","tsumogiri":false},
{"type":"tsumo","actor":0,"pai":"6m"}]
-> {"type":"kakan","actor":0,"pai":"6m","consumed":["6m","6m","6m"]}
<- [{"type":"kakan","actor":0,"pai":"6m","consumed":["6m","6m","6m"]},
{"type":"tsumo","actor":0,"pai":"1p"}]
-> {"type":"dahai","actor":0,"pai":"2p","tsumogiri":false}
<- [{"type":"dahai","actor":0,"pai":"2p","tsumogiri":false},
{"type":"dora","dora_marker":"3s"},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"3s","tsumogiri":true},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"7p","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"N","tsumogiri":true},
{"type":"tsumo","actor":0,"pai":"7p"}]
```

### Call: Daiminkan

ankou (3) + 1 other discard

```
<- [{"type":"tsumo","actor":0,"pai":"9p","tsumogiri":false},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"7s","tsumogiri":false},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"5m","tsumogiri":true}]
-> {"type":"daiminkan","actor":0,"target":2,"pai":"5m","consumed":["5m","5m","5mr"]}
<- [{"type":"daiminkan","actor":0,"target":2,"pai":"5m","consumed":["5m","5m","5mr"]},
{"type":"tsumo","actor":0,"pai":"1p"}]
-> {"type":"dahai","actor":0,"pai":"2p","tsumogiri":false}
<- [{"type":"dahai","actor":0,"pai":"2p","tsumogiri":false},
{"type":"dora","dora_marker":"3s"},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"3s","tsumogiri":true},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"7p","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"N","tsumogiri":true},
{"type":"tsumo","actor":0,"pai":"7p"}]
```

### Call: Ankan

```
<- [{"type":"tsumo","actor":0,"pai":"9p","tsumogiri":false},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"7s","tsumogiri":false},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"F","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"2m","tsumogiri":false},
{"type":"tsumo","actor":0,"pai":"F"}]
-> {"type":"ankan","actor":0,"consumed":["F","F","F","F"]}
<- [{"type":"ankan","actor":0,"consumed":["F","F","F","F"]},
{"type":"tsumo","actor":0,"pai":"1p"}]
-> {"type":"dahai","actor":0,"pai":"2p","tsumogiri":false}
<- [{"type":"dahai","actor":0,"pai":"2p","tsumogiri":false},
{"type":"dora","dora_marker":"3s"},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"3s","tsumogiri":true},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"7p","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"N","tsumogiri":true},
{"type":"tsumo","actor":0,"pai":"7p"}]
```

### Reach

```
<- [{"type":"dahai","actor":0,"pai":"3s","tsumogiri":true},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"3m","tsumogiri":false},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"7p","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"N","tsumogiri":true},
{"type":"tsumo","actor":0,"pai":"7p"}]
-> {"type":"reach","actor":0}
<- [{"type":"reach","actor":0}]
-> {"type":"dahai","pai":"3p","actor":0,"tsumogiri":false}
<- [{"type":"reach_accepted","actor":0},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"dahai","actor":1,"pai":"4s","tsumogiri":false},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"2m","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"3s","tsumogiri":true},
{"type":"tsumo","actor":0,"pai":"1m"}]
-> {"type":"dahai","pai":"1m","actor":0,"tsumogiri":true}
```

### Hora (Ron Agari)

After hora, end_kyoku event follows. If the game is not finished, the start_kyoku event follows and the next kyoku (局; round) starts.

```
<- [{"type":"dahai","actor":1,"pai":"3m","tsumogiri":true},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"F","tsumogiri":false},
{"type":"tsumo","actor":3,"pai":"?"},
{"type":"dahai","actor":3,"pai":"C","tsumogiri":true}]
-> {"type":"hora","actor":1,"target":3,"pai":"C"}
<- [{"type":"end_kyoku"}]
-> {"type":"none"}
<- [{"type":"start_kyoku","bakaze":"E","dora_marker":"2m",
"kyoku":1,"honba":1,"kyotaku":0,"oya":0,"scores":[34600,21800,21800,21800],
"tehais":[["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["1m","3s","W","8p","1m","4s","8p","2p","7s","1s","7p","1s","9s"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"]]},
{"type":"tsumo","actor":0,"pai":"?"},
{"type":"dahai","actor":0,"pai":"5sr","tsumogiri":false}]
-> {"type":"none"}
```

Hora (Tsumo Agari)

```
<- [{"type":"dahai","actor":3,"pai":"E","tsumogiri":true},
{"type":"tsumo","actor":0,"pai":"?"},
{"type":"dahai","actor":0,"pai":"1p","tsumogiri":false},
{"type":"tsumo","actor":1,"pai":"?"},
{"type":"tsumo","actor":2,"pai":"?"},
{"type":"dahai","actor":2,"pai":"2m","tsumogiri":true},
{"type":"tsumo","actor":3,"pai":"5s"}]
-> {"type":"hora","actor":3,"target":3}
<- [{"type":"end_kyoku"}]
-> {"type":"none"}
<- [{"type":"end_game"}]
-> {"type":"none"}
```

### Ryukyoku

Abortive draws by kyuusyu-kyuuhai (Nine terminals abortion; 九種九牌).

```
<- [{"type":"start_kyoku",,"bakaze":"E","dora_marker":"2s",
"kyoku":1,"honba":0,"kyotaku":0,"oya":0,
"scores":[25000,25000,25000,25000],
"tehais":[
["1m","9m","1p","9p","1s","1s","E","E","S","S","S","P","F"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"],
["?","?","?","?","?","?","?","?","?","?","?","?","?"]
]},{"type":"tsumo","actor":0,"pai":"C"}]
-> {"type":"ryukyoku"}
```

