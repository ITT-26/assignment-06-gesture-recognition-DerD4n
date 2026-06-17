"""
ASCII art for the Spell Duel stick-figure wizards.
All art is plain strings, rendered with a monospace pyglet font.
partialy ai generated but the basic character designs and spells were mine and i will not take any criticism :)
"""

PLAYER_IDLE = r"""
      /\
     /  \
    /____\
    |o  o|
    | /\ |
    |____|
   /|====|\
  / |====| \
    | || |
    | || |
   /__||__\
"""

PLAYER_CAST = r"""
      /\
     /  \
    /____\
    |>  <|
    | /\ |
   *|____|*
  / |====| \
 *  |====|  *
    | || |
    | || |
   /__||__\
"""

PLAYER_HIT = r"""
      /\
     /x \
    /____\
    |x  x|
    | oo |
    |____|
   /|====|\
  / |====| \
    | || |
   x| || |x
   /__||__\
"""

AI_IDLE_1 = r"""
     /\
    /  \
   | () |
    \--/
   --||--
  |  ||  |
  |  ||  |
     ||
    /  \
   /    \
"""

AI_CAST_1 = r"""
     /\
    /  \
   | >< |
   *\--/*
  --||--
 \  ||  /
  \ || /
     ||
    /  \
   /    \
"""

AI_HIT_1 = r"""
     /\
    / x\
   |x()x|
    \--/
   --||--
x |  ||  | x
  |  ||  |
     ||
   x/  \x
   /    \
"""

AI_IDLE_2 = r"""
       /^^\
      /____\
      |\  /|
      | >< |
      |____|
    __/||||\__
      /||||\
     / |||| \
       ||||
      /  \\
"""

AI_CAST_2 = r"""
       /^^\
      /____\
     *|\  /|*
      |><> |
     *|____|*
    __/||||\__
   *  /||||\  *
     / |||| \
       ||||
       /  \\
"""

AI_HIT_2 = r"""
       /^^\
      /_x__\
      |x  x|
      | vv |
      |____|
    __/||||\__
   x  /||||\  x
     / |||| \
     x |||| x
       /  \\
"""


# ----------------------------------------------------------------
# Spell visual effects (shown briefly when a spell is cast/lands)
# ----------------------------------------------------------------

SPELL_FX = {

    "fire": [
r"""
    .
   ( )
""",
r"""
     )
   (###)
    ###
""",
r"""
    ((#))
  ((#####))
    \|||/
"""
    ],

    "earth": [
r"""
     ^
""",
r"""
    /^\
   /___\
""",
r"""
      /\
     /  \
    /____\
   /_/||\_\
"""
    ],

    "lightning": [
r"""
      /
""",
r"""
     /\
    /
""",
r"""
      /\
     /
   /\/\
      \/
"""
    ],

    "water": [
r"""
    ~ ~
""",
r"""
   ~~~~~
  ~~ ~ ~~
""",
r"""
  ~~~~~~~~
 ~~ ~~~~ ~~
  ~~~~~~~~
"""
    ],

    "holy": [
r"""
      *
""",
r"""
      *
    --+--
""",
r"""
       *
    \  |  /
  ---\ + /---
    /  |  \
       *
"""
    ],

    "shield": [
r"""
       ()
""",
r"""
      /  \
     |    |
      \__/
""",
r"""
     .-----.
   .'  /\   '.
  /   /  \    \
  \   \__/    /
   '._    __.'
      '----'
"""
    ],

    "fizzle": [
r"""
      .
""",
r"""
    . . .
""",
r"""
   .  x  .
    .   .
      .
"""
    ],
}


def fx_for(element_key):
    return SPELL_FX.get(element_key, SPELL_FX["fizzle"])