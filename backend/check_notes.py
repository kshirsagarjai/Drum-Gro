import mido

# Show all connected MIDI devices
print("Connected MIDI ports:")
for i, name in enumerate(mido.get_input_names()):
    print(f"  [{i}] {name}")

# Open the first port and listen
port_name = mido.get_input_names()[0]
print(f"\nListening on: {port_name}")
print("Hit each pad ONE AT A TIME. Press Ctrl+C to stop.\n")

with mido.open_input(port_name) as port:
    for msg in port:
        if msg.type == "note_on" and msg.velocity > 0:
            print(f"Note: {msg.note}   Velocity: {msg.velocity}")
