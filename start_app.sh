#!/bin/bash
# start_app.sh - Start de storingskoffer in de virtuele omgeving.
# RET N.V. | Said Keteldijk (1045604)

cd "$(dirname "$0")" || exit 1

# Wacht tot de grafische sessie er is. Zonder scherm valt main.py terug op
# het offscreen-platform en verschijnt er nooit iets.
for _ in $(seq 1 30); do
    [ -e /tmp/.X11-unix/X0 ] && break
    sleep 1
done

source venv-rpi/bin/activate

# -u zodat de meldingen van de app direct in het journaal staan.
exec python3 -u main.py
