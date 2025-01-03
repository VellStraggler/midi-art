import rtmidi
import time
import pygame
import pygame.midi
from mido import MidiFile, MidiTrack, Message, MetaMessage

SCREEN_WIDTH = 1280  # Width for pitch mapping
SCREEN_HEIGHT = 720  # Height for time looping (8 seconds)
DIMENSIONS = (SCREEN_WIDTH, SCREEN_HEIGHT)
FULL_SCREEN = pygame.Rect((0, 0), DIMENSIONS)
PITCH_MIN = 36  # Minimum MIDI pitch to display
PITCH_MAX = 84  # Maximum MIDI pitch to display
KEY_WIDTH = SCREEN_WIDTH / (PITCH_MAX - PITCH_MIN)
TIME_LOOP = 8  # Loop duration in seconds
BLACK_KEYS = (1,3,6,8,10)

SKIN_TONE = ((233, 162, 74))
WHITE = ((255,255,255))
BROWN = ((97, 34, 16))
YELLOW = ((247, 253, 23))
SKY = ((65,200,253))
GREEN = ((75,182,81))
BLACK = ((0,0,0))
NOTE_COLORS = [(255, 3, 5), SKIN_TONE, (16, 68, 126), BROWN, YELLOW, BLACK, GREEN]
LINE_WIDTH = 4
KEY_BORDER_RADIUS = 16

def setup_midi_output():
    pygame.midi.init()
    return pygame.midi.Output(pygame.midi.get_default_output_id())

def play_note(midi_output, pitch, velocity):
    if velocity > 0:
        midi_output.note_on(pitch, velocity)
    else:
        midi_output.note_off(pitch)

def play_special_note(midi_output, pitch, velocity= 50):
    midi_output.set_instrument(5)
    play_note(midi_output, pitch, velocity)
    midi_output.set_instrument(0)

def main():
    pygame.init()
    screen = pygame.display.set_mode(DIMENSIONS)
    pygame.display.set_caption("MIDI Visualizer with Persistent Notes")

    midi_in = rtmidi.MidiIn()
    midi_output = setup_midi_output()
    available_ports = midi_in.get_ports()

    if not available_ports:
        print("No MIDI devices connected.")
        return

    # Open the second-to-last connected device
    # Novation LaunchKey 49 connects as 2 MIDI devices, so we use the first one
    latest_device_index = len(available_ports) - 2
    midi_in.open_port(latest_device_index)
    print(f"Connected to device: {available_ports[latest_device_index]}")

    # List to keep track of drawn notes as persistent "trails"
    drawn_notes = [] # List
    held_notes = {} # Set

    color_index = 0
    draw_background(screen)
    background_image = screen.copy()

    clock = pygame.time.Clock()
    max_height = radius_from_velocity(128) * 2

    pause_time = False
    up_time = False
    down_time = False
    
    last_loop_time = time.time()
    current_time = 0

    # DEV-ONLY OPTIONS:
    auto_color = True
    scrolling = False
    gradients = False
    
    take_screenshot = False
    recording = False
    playing = False
    paused = False
    midi_messages = []
    midi_file = None
    next_note_time = time.perf_counter()
    play_filename = "recorded_output.mid"

    run_program = True

    try:
        while run_program:
            # print(str(len(drawn_notes)))
            # current_time = time.time() - start_time
            if (not pause_time):
                current_time += 1/60
            looped_time = current_time % TIME_LOOP  # Wrap time into an 8-second loop
            time_to_reset = int(current_time / TIME_LOOP)  # Detect loop reset for color change

            # Change the color every time the loop resets (every 8 seconds)
            if time_to_reset != last_loop_time:
                last_loop_time = time_to_reset
                if(auto_color):
                    color_index = (color_index + 1) % len(NOTE_COLORS)
                midi_output.note_off(43)
                midi_output.note_off(88)

            # COMMANDS
            for event in pygame.event.get():
                # End Program
                if event.type == pygame.QUIT:
                    run_program = False
                elif event.type == pygame.KEYDOWN:
                    # Change Color
                    if event.key == pygame.K_SPACE:
                        last_loop_time = time_to_reset
                        color_index = (color_index + 1) % len(NOTE_COLORS)
                        play_special_note(midi_output, 88)
                    # Clear Screen
                    elif event.key == pygame.K_e:
                        drawn_notes = []
                        draw_background(screen)
                        background_image = screen.copy()
                        play_special_note(midi_output, 43, 100)
                    # Pause Movement
                    elif event.key == pygame.K_LSHIFT:
                        pause_time = True
                        play_special_note(midi_output, 76, 30)
                    # Move bar up
                    elif event.key == pygame.K_w:
                        up_time = True
                    # Move bar down
                    elif event.key == pygame.K_s:
                        down_time = True
                    # Undo Button
                    elif event.key == pygame.K_z:
                        if (len(drawn_notes) != 0):
                            note_removed = drawn_notes.pop()
                            # iterate backwards to find all notes that have
                            # the same pitch and close to the same time
                            i = len(drawn_notes) -1
                            while i > -1:
                                note = drawn_notes[i]
                                if (note[3] == note_removed[3] and note[2] == note_removed[2] and
                                    (note[1] + 6 > note_removed[1] and note[1] - 6 < note_removed[1])):
                                    note_removed = drawn_notes.pop(i)
                                i -= 1
                    # (R)ecord MIDI Button
                    elif event.key == pygame.K_r and not playing:
                        recording = not recording
                        print("Pressed recording to " + str(recording))
                    # (P)lay MIDI Button
                    # Cannot record and play at same time
                    elif event.key == pygame.K_p and not recording:
                        if not playing:
                            print("playing audio file: " + play_filename)
                            playing = True
                            midi_messages = []
                            midi_file = MidiFile(play_filename)
                            # Outputs note messages only by default
                            for message in midi_file:
                                midi_messages.append(message)
                            # Start playing right NOW
                            next_note_time = time.perf_counter() # + midi_messages[0].time
                        else:
                            if paused:
                                paused = False
                                next_note_time = time.perf_counter()
                            else:
                                paused = True
                    # (Q)uit
                    elif event.key == pygame.K_q:
                        run_program = False
                    # (T)ake Screenshot
                    elif event.key == pygame.K_t:
                        take_screenshot = True
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_LSHIFT:
                        pause_time = False
                        play_special_note(midi_output, 72, 30)
                    if event.key == pygame.K_w:
                        up_time = False
                    if event.key == pygame.K_s:
                        down_time = False

            # Process all incoming MIDI messages
            while True:
                if (up_time):
                    current_time -= 8/60
                elif (down_time):
                    current_time += 6/60
                if (not recording and len(midi_messages) > 0 and not playing):
                    # Save to a MIDI File
                    print("beginning save with " + str(len(midi_messages)))
                    midi_file = MidiFile()
                    track = MidiTrack()
                    # track.append(MetaMessage('set_tempo', tempo=500000)) #supposedly 120 BPM
                    midi_file.tracks.append(track)
                    for msg in midi_messages:
                        track.append(msg)

                    #Write to given filename
                    output_filename = "recorded_output" + str(int(time.time()%10000)) + ".mid"
                    midi_file.save(output_filename)
                    midi_messages = []
                    print("saved")
                
                # Accept input from the user
                msg = midi_in.get_message()
                if not msg:
                    # Play from the recorded midi file if the user has not played that very millisecond
                    if (playing and not paused):
                        # Things will generally be played on time, but not exactly when the user is playing too
                        if next_note_time <= time.perf_counter():
                            if not isinstance(midi_messages[0],MetaMessage):
                                if midi_messages[0].velocity != 0:
                                    # Construct message that can be read
                                    message = (144, midi_messages[0].note, midi_messages[0].velocity)
                                    msg = (message, midi_messages[0].time)
                                else:
                                    message = (128, midi_messages[0].note, 0)
                                    msg = (message, midi_messages[0].time)
                            if len(midi_messages) != 0:
                                midi_messages = midi_messages[1:]
                                if len(midi_messages) != 0:
                                    next_note_time += midi_messages[0].time
                        if len(midi_messages) == 0:
                            playing = False
                            print("playing finished")
                if not msg:
                    break
                else:
                    message, delta_time = msg
                    status, pitch, velocity = message

                    # Record MIDI input
                    if (recording):
                        print(len(midi_messages))
                        mido_message = Message.from_bytes(message)
                        mido_message.time = int(delta_time * 1000)
                        midi_messages.append(mido_message)
                        print(mido_message)

                    # Play or stop the note based on Note On/Off status
                    if status == 144 and velocity > 0:  # Note On)
                        play_note(midi_output, pitch, velocity)
                        # Calculate x and y for the note based on pitch and time
                        # Save position, color index, and pitch to drawn_notes list (for persistent notes)
                        held_notes[pitch] = velocity
                    elif status == 128:# or (status == 144 and velocity == 0):  # Note Off
                        play_note(midi_output, pitch, 0)
                        
                        if pitch in held_notes:
                            held_notes.pop(pitch)
                        # No removal of notes, only updating color on loop reset

            # Clear and update the screen with the known background image
            # Only update around the marker line up to the height of the largest possible circle
            time_marker_y = int((looped_time / TIME_LOOP) * SCREEN_HEIGHT)
            screen.blit(background_image, FULL_SCREEN, FULL_SCREEN)

            if(scrolling):
                time_marker_y = int(SCREEN_HEIGHT - (LINE_WIDTH * 4))
                i = len(drawn_notes) -1
                while i > -1:
                    note = drawn_notes[i]
                    if (note[1] < -max_height):
                        drawn_notes.pop(i)
                    else:
                        list_note = list(note)
                        list_note[1] -= 2
                        drawn_notes[i] = tuple(list_note)
                    i -= 1

            # Add all held notes to the drawn notes at the y-level in which they are pressed
            time_pressed = time.perf_counter()
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                if held_notes.get(pitch) > 1:
                    drawn_notes.append((x, time_marker_y, color_index, pitch, held_notes.get(pitch), time_pressed))


            # Draw all notes that are OVER 30 seconds old
            first_expired_index = -1
            for i in range(len(drawn_notes)):
                x, y, one_color_index, pitch, velocity, time_to_reset = drawn_notes[i]
            # for x, y, one_color_index, pitch, velocity, time_to_reset in drawn_notes:
                # if note is 30 seconds old, get rid of 
                if time_pressed > time_to_reset + 30:
                    first_expired_index += 1
                else:
                    break
                color = NOTE_COLORS[one_color_index]  # Get color based on the color index
                if (gradients):
                    if (scrolling):
                        b=.3
                        drawn_time = (SCREEN_HEIGHT/2) - y
                    else:
                        b=7
                        drawn_time = - (time_pressed - time_to_reset)
                    new_color = list(color)
                    for i in range(3):
                        new_color[i] = min(255,max(0,color[i] + (b*drawn_time)))
                        # print(new_color)
                    color = tuple(new_color)
                pygame.draw.circle(screen, color, (x, y), radius_from_velocity(velocity))

            # Remove all notes that are OLDER than 30 seconds and replace with a photo
            if (first_expired_index > -1):
                # Update the whole screen just once
                background_image = screen.copy()
                drawn_notes = drawn_notes[first_expired_index:]

            for x, y, one_color_index, pitch, velocity, time_to_reset in drawn_notes:
                color = NOTE_COLORS[one_color_index]  # Get color based on the color index
                if (gradients):
                    if (scrolling):
                        b=.3
                        drawn_time = (SCREEN_HEIGHT/2) - y
                    else:
                        b=7
                        drawn_time = - (time_pressed - time_to_reset)
                    new_color = list(color)
                    for i in range(3):
                        new_color[i] = min(255,max(0,color[i] + (b*drawn_time)))
                        # print(new_color)
                    color = tuple(new_color)
                pygame.draw.circle(screen, color, (x, y), radius_from_velocity(velocity))

            if take_screenshot:
                pygame.image.save(screen,"screenshot.png")
                take_screenshot = False

            # Draw the time marker line
            if time_marker_y < SCREEN_HEIGHT -2:
                color = NOTE_COLORS[color_index]
                if scrolling: color = BLACK
                bright = 380
                key_color = WHITE
                if color[0] + color[1] > bright or color[1] + color[2] > bright or color[2] + color[0] > bright:
                    key_color = BLACK
                pygame.draw.line(screen, key_color, (0, time_marker_y), (SCREEN_WIDTH, time_marker_y), LINE_WIDTH * 3)
                for i in range(PITCH_MAX - PITCH_MIN):
                    start_pos = i * KEY_WIDTH - (KEY_WIDTH //2)
                    if((i%12) in BLACK_KEYS):
                        pygame.draw.line(screen, color, (start_pos + (KEY_WIDTH//2), time_marker_y - (LINE_WIDTH*1.5)), (start_pos + (KEY_WIDTH//2), time_marker_y + (LINE_WIDTH*1.5)), LINE_WIDTH)
                        pygame.draw.line(screen, color, (start_pos, time_marker_y - LINE_WIDTH), (start_pos + KEY_WIDTH, time_marker_y - LINE_WIDTH), LINE_WIDTH * 2)
                    elif (i%12 in (5,0)):
                        pygame.draw.line(screen, color, (start_pos, time_marker_y - (LINE_WIDTH*1.5)), (start_pos, time_marker_y + (LINE_WIDTH*1.5)), LINE_WIDTH)
            multiplier = 1
            if scrolling:
                multiplier = 2
            # Outline all held notes (blends them together)
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                # draw outline only for currently held notes on the marker line
                draw_circle_to_rect_gradient(screen, WHITE, (x, time_marker_y), radius_from_velocity(held_notes.get(pitch)) * multiplier, True)
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                # draws color over outline for currently held notes on the marker line
                color = NOTE_COLORS[one_color_index]
                draw_circle_to_rect_gradient(screen, color, (x, y), (radius_from_velocity(held_notes.get(pitch)) - LINE_WIDTH) * multiplier)

            # Draw held notes as darkened key notes
            for pitch in held_notes:
                x = int(((pitch - PITCH_MIN) / (PITCH_MAX - PITCH_MIN)) * SCREEN_WIDTH)
                color = (NOTE_COLORS[one_color_index])
                color = (max(0,color[0]-50),max(0,color[1]-50),max(0,color[2]-50))
                pygame.draw.rect(screen, color, ((x - (KEY_WIDTH), time_marker_y - (LINE_WIDTH*3)),(KEY_WIDTH*2 + LINE_WIDTH//2, (LINE_WIDTH * 6))),
                                border_radius=KEY_BORDER_RADIUS)

                # Decrease the pitch over time
                velocity = held_notes.get(pitch)
                # held_notes.update({pitch: max(0, (velocity -.1 - 10000/max(1,pow(velocity,3))))})
                # held_notes.update({pitch: max(0, velocity*.9933 - (4/max(1,velocity)))})
                held_notes.update({pitch: max(0, velocity*.997 - (4.5/max(1,velocity)))})


            # Draw the hint for the next colors at the end of it
            hint = 16
            pygame.draw.circle(screen, NOTE_COLORS[(color_index + 2)%len(NOTE_COLORS)], (SCREEN_WIDTH - (hint*.2), time_marker_y), hint * .5)
            pygame.draw.circle(screen, NOTE_COLORS[(color_index + 1)%len(NOTE_COLORS)], (SCREEN_WIDTH - (hint* 1.05), time_marker_y), hint * .72)
            pygame.draw.circle(screen, NOTE_COLORS[(color_index)], (SCREEN_WIDTH - (hint* 2.15), time_marker_y), hint)

            # flip to newly drawn display
            pygame.display.flip()
            clock.tick(60)

    except KeyboardInterrupt:
        print("Exiting.")

    finally:
        midi_in.close_port()
        midi_output.close()
        pygame.midi.quit()
        pygame.quit()

def radius_from_velocity(v):
    """give a number from 1 to 127"""
    # return v * v * .007
    # return (pow(v - 70,3)/17150) + (.5*v) + 20
    # return (pow(v-50,3)/7600) + (.316*v) + 17
    return (pow(v-40,3)/9600) + (.416*v) + 7
    # return v*v//127

def draw_background(screen: pygame.Surface):
    pygame.draw.rect(screen, SKY, FULL_SCREEN)
    # pygame.draw.rect(screen, BLACK, FULL_SCREEN)
    # image_surface = pygame.image.load("mario.png")
    # screen.blit(image_surface, FULL_SCREEN)

def draw_circle_to_rect_gradient(surface: pygame.Surface, color, center, radius: float, outline: bool = False):
    if (radius < KEY_BORDER_RADIUS * 3):
        if outline:
            radius = int(max(KEY_BORDER_RADIUS *2, radius))
        else:
            radius = int(max(KEY_BORDER_RADIUS, radius))
        y_shrink = (pow(radius-KEY_BORDER_RADIUS,2))/(KEY_BORDER_RADIUS//2) + KEY_BORDER_RADIUS
        # I tried a lot of curves, this one is the best ^
        # y_shrink = max((pow(radius-(KEY_BORDER_RADIUS*2),3))*.020 - (KEY_BORDER_RADIUS*3) + (radius*3), radius)
        # y_shrink = 6* (radius - 24)
        # y_shrink = log(max(radius-31,1),10) * 74 + 48
        pygame.draw.rect(surface, color, (center[0]-radius, center[1]-(y_shrink/3),radius*2,(2 * y_shrink//3)),
                         border_radius=radius)
    else:
        pygame.draw.circle(surface, color, center, radius)

if __name__ == "__main__":
    main()