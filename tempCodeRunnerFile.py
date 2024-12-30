lor)
                    for i in range(3):
                        new_color[i] = min(255,max(0,color[i] + (b*drawn_time)))
                    color = tuple(new