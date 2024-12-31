ne_color_index, pitch, velocity, time_to_reset in drawn_notes:
            #     color = NOTE_COLORS[one_color_index]  # Get color based on the color index
            #     if (gradients):
            #         if (scrolling):
            #             b=.3
            #             drawn_time = (SCREEN_HEIGHT/2) - y
            #         else:
            #             b=7
            #             drawn_time = - (time_pressed - time_to_reset)
            #         new_color = list(color)
            #         for i in range(3):
            #             new_color[i] = min(255,max(0,color[i] + (b*drawn_time)))
            #             # print(new_color)
            #         color = tuple(new_color)
            #     pygame.draw.circle(scree