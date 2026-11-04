"""Writes the case batches 04-07 for the v2 design (record of what was sent).
Run: python3 -I cad/batches/v2/make_batches.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import profiles as P
L, W = P.L, P.W
COLS = [("col_off", "col_off"), ("case_length-col_off", "col_off"), ("col_off", "case_width-col_off"), ("case_length-col_off", "case_width-col_off")]
COLS_NUM = [(6, 6), (L - 6, 6), (6, W - 6), (L - 6, W - 6)]
def save(name, C):
    json.dump({"commands": C}, open(os.path.join(HERE, name), "w"), indent=1)

# 04 base: shell with corner columns, plate ledge, insert holes, openings
C = [{"command": "solid.box", "params": {"length": "case_length", "width": "case_width", "height": "base_height", "corner": [0, 0, 0], "operation": "new", "body_name": "case.base", "name": "Base blank"}},
     {"command": "solid.fillet", "params": {"body": "case.base", "edges": [[0, 0, 15], [L, 0, 15], [0, W, 15], [L, W, 15]], "radius": "corner_radius", "name": "Base corners"}},
     {"command": "sketch.create", "params": {"plane": "XY", "offset": "plate_top-plate_t", "name": "Upper cavity outline"}}]
C += P.loop(2.4, 5.5, 1.5)
C += [{"command": "sketch.finish", "params": {}},
      {"command": "solid.extrude", "params": {"sketch": "Upper cavity outline", "distance": "base_height-(plate_top-plate_t)+1 mm", "operation": "cut", "targets": ["case.base"], "name": "Upper cavity"}},
      {"command": "sketch.create", "params": {"plane": "XY", "offset": "wall", "name": "Lower cavity outline"}}]
C += P.loop(3.9, 7.0, 1.5)
C += [{"command": "sketch.finish", "params": {}},
      {"command": "solid.extrude", "params": {"sketch": "Lower cavity outline", "distance": "plate_top-plate_t-wall+0.5 mm", "operation": "cut", "targets": ["case.base"], "name": "Lower cavity"}}]
for i, (x, y) in enumerate(COLS, 1):
    C.append({"command": "solid.cylinder", "params": {"diameter": "insert_hole_d", "height": "insert_len+2 mm", "base": [x, y, "base_height-insert_len-1 mm"], "operation": "cut", "targets": ["case.base"], "name": f"Insert hole {i}"}})
C += [{"command": "solid.box", "params": {"length": "usb_open_w", "width": "wall+2 mm", "height": "base_height-usb_open_bottom+1 mm", "corner": ["esp32_x-usb_open_w/2", "-1 mm", "usb_open_bottom"], "operation": "cut", "targets": ["case.base"], "name": "USB opening"}},
      {"command": "solid.cylinder", "params": {"diameter": "sma_hole_d", "height": "wall+2 mm", "base": ["case_length-wall-1 mm", "sma_axis_y", "sma_axis_z"], "axis": "X", "operation": "cut", "targets": ["case.base"], "name": "SMA slot round"}},
      {"command": "solid.box", "params": {"length": "wall+2 mm", "width": "sma_hole_d", "height": "base_height-sma_axis_z+1 mm", "corner": ["case_length-wall-1 mm", "sma_axis_y-sma_hole_d/2", "sma_axis_z"], "operation": "cut", "targets": ["case.base"], "name": "SMA slot open top"}}]
save("04-base.json", C)

# 05 plate: drop-in mounting plate with header windows and board pockets
Z = "plate_top-plate_t-1 mm"; H = "plate_t+2 mm"
C = [{"command": "sketch.create", "params": {"plane": "XY", "offset": "plate_top-plate_t", "name": "Plate outline"}}]
C += P.loop(2.7, 5.8, 1.2)
C += [{"command": "sketch.finish", "params": {}},
      {"command": "solid.extrude", "params": {"sketch": "Plate outline", "distance": "plate_t", "operation": "new", "body_name": "case.plate", "name": "Mounting plate"}}]
def cut(name, corner, l, w):
    C.append({"command": "solid.box", "params": {"length": l, "width": w, "height": H, "corner": corner, "operation": "cut", "targets": ["case.plate"], "name": name}})
def rim(name, corner, l, w):
    C.append({"command": "solid.box", "params": {"length": l, "width": w, "height": "pocket_rim_h+0.5 mm", "corner": corner + ["plate_top-0.5 mm"], "operation": "join", "targets": ["case.plate"], "name": name}})
cut("ESP header window left", ["esp32_x-12 mm-1.6 mm", "esp32_y-19.9 mm", Z], "3.2 mm", "39.8 mm")
cut("ESP header window right", ["esp32_x+12 mm-1.6 mm", "esp32_y-19.9 mm", Z], "3.2 mm", "39.8 mm")
cut("Radio header window", ["radio_x-15.6 mm", "radio_y-7.95 mm", Z], "5.5 mm", "15.9 mm")
cut("SMA flange notch", ["radio_x+12.2 mm", "radio_y-1.8 mm", Z], "5 mm", "7.6 mm")
t = "pocket_rim_t"
rim("ESP pocket left", ["esp32_x-14 mm-fit_gap-pocket_rim_t", "esp32_y-19.5 mm"], t, "39 mm")
rim("ESP pocket right", ["esp32_x+14 mm+fit_gap", "esp32_y-19.5 mm"], t, "39 mm")
rim("ESP pocket front", ["esp32_x-12 mm", "esp32_y-25.5 mm-fit_gap-pocket_rim_t"], "24 mm", t)
rim("Radio pocket front", ["radio_x-14.5 mm", "radio_y-8 mm-fit_gap-pocket_rim_t"], "26 mm", t)
rim("Radio pocket back", ["radio_x-14.5 mm", "radio_y+8 mm+fit_gap"], "26 mm", t)
rim("Radio pocket header end", ["radio_x-15.5 mm-fit_gap-pocket_rim_t", "radio_y-6 mm"], t, "12 mm")
save("05-plate.json", C)

# 06 lid: plate, locating rim round walls and columns, screw holes, SMA tongue, hold-downs
C = [{"command": "solid.box", "params": {"length": "case_length", "width": "case_width", "height": "lid_t", "corner": [0, 0, "base_height"], "operation": "new", "body_name": "case.lid", "name": "Lid blank"}},
     {"command": "solid.fillet", "params": {"body": "case.lid", "edges": [[0, 0, 32.5], [L, 0, 32.5], [0, W, 32.5], [L, W, 32.5]], "radius": "corner_radius", "name": "Lid corners"}},
     {"command": "sketch.create", "params": {"plane": "XY", "offset": "base_height-lip_h", "name": "Lid rim outline"}}]
C += P.loop(2.7, 5.8, 1.2)
C += P.loop(4.3, 7.4, 0)
C += [{"command": "sketch.finish", "params": {}},
      {"command": "solid.extrude", "params": {"sketch": "Lid rim outline", "distance": "lip_h+0.5 mm", "operation": "new", "body_name": "case.lid_rim", "name": "Lid rim"}},
      {"command": "solid.box", "params": {"length": "usb_open_w", "width": "wall+fit_gap+lip_t+2 mm", "height": "lip_h+2 mm", "corner": ["esp32_x-usb_open_w/2", "-1 mm", "base_height-lip_h-1 mm"], "operation": "cut", "targets": ["case.lid_rim"], "name": "Lid rim USB plug gap"}},
      {"command": "solid.combine", "params": {"target": "case.lid", "tools": ["case.lid_rim"], "operation": "join"}}]
for i, (x, y) in enumerate(COLS, 1):
    C.append({"command": "solid.cylinder", "params": {"diameter": "m4_clear_d", "height": "lid_t+2 mm", "base": [x, y, "base_height-1 mm"], "operation": "cut", "targets": ["case.lid"], "name": f"Lid screw hole {i}"}})
    C.append({"command": "solid.cylinder", "params": {"diameter": "m4_cb_d", "height": "m4_cb_depth+1 mm", "base": [x, y, "base_height+lid_t-m4_cb_depth"], "operation": "cut", "targets": ["case.lid"], "name": f"Lid counterbore {i}"}})
C += [{"command": "solid.box", "params": {"length": "wall-0.2 mm", "width": "sma_hole_d-0.4 mm", "height": "base_height+0.5 mm-(sma_axis_z+1.5 mm)", "corner": ["case_length-wall", "sma_axis_y-sma_hole_d/2+0.2 mm", "sma_axis_z+1.5 mm"], "operation": "join", "targets": ["case.lid"], "name": "SMA tongue"}},
      {"command": "solid.cylinder", "params": {"diameter": "sma_hole_d", "height": "wall+1 mm", "base": ["case_length-wall", "sma_axis_y", "sma_axis_z"], "axis": "X", "operation": "cut", "targets": ["case.lid"], "name": "SMA tongue arch"}}]
for nm, (x, y) in {"ESP hold-down 1": ("esp32_x-13.7 mm", "esp32_y-21.3 mm"), "ESP hold-down 2": ("esp32_x+11.2 mm", "esp32_y-21.3 mm"), "ESP hold-down 3": ("esp32_x-13.7 mm", "esp32_y+18.8 mm"), "ESP hold-down 4": ("esp32_x+11.2 mm", "esp32_y+18.8 mm")}.items():
    C.append({"command": "solid.box", "params": {"length": "2.5 mm", "width": "2.5 mm", "height": "base_height+0.5 mm-(plate_top+1.6 mm+holddown_gap)", "corner": [x, y, "plate_top+1.6 mm+holddown_gap"], "operation": "join", "targets": ["case.lid"], "name": nm}})
C += [{"command": "solid.box", "params": {"length": "8 mm", "width": "6 mm", "height": "base_height+0.5 mm-(plate_top+3.9 mm+holddown_gap)", "corner": ["radio_x-5.75 mm", "radio_y-3 mm", "plate_top+3.9 mm+holddown_gap"], "operation": "join", "targets": ["case.lid"], "name": "Radio hold-down on shield"}},
      {"command": "solid.box", "params": {"length": "1.8 mm", "width": "15 mm", "height": "base_height+0.5 mm-(plate_top+1.6 mm+holddown_gap)", "corner": ["radio_x+10.4 mm", "radio_y-7.5 mm", "plate_top+1.6 mm+holddown_gap"], "operation": "join", "targets": ["case.lid"], "name": "Radio hold-down rib at SMA"}}]
save("06-lid.json", C)

# 07 hardware and colours
C = []
for i, (x, y) in enumerate(COLS_NUM, 1):
    C.append({"command": "solid.cylinder", "params": {"diameter": "6.3 mm", "height": "insert_len", "base": [x, y, "base_height-insert_len-0.1 mm"], "operation": "new", "body_name": f"hardware.m4_insert-{i}", "name": f"M4 heat-set insert {i}"}})
    C.append({"command": "solid.cylinder", "params": {"diameter": "4 mm", "height": "insert_len+2 mm", "base": [x, y, "base_height-insert_len-1 mm"], "operation": "cut", "targets": [f"hardware.m4_insert-{i}"], "name": f"M4 insert bore {i}"}})
for i, (x, y) in enumerate(COLS_NUM, 1):
    C.append({"command": "parts.insert", "params": {"family": "button_head_cap_screw", "size": "M4", "length": 10, "point": [x, y, 32.2], "direction": [0, 0, 1], "name": f"Lid screw {i}"}})
C += [{"command": "appearance.assign", "params": {"bodies": ["case.base"], "color": "#3d4248"}},
      {"command": "appearance.assign", "params": {"bodies": ["case.plate"], "color": "#7d8a94"}},
      {"command": "appearance.assign", "params": {"bodies": ["case.lid"], "color": "#dc6c24"}},
      {"command": "appearance.assign", "params": {"bodies": [f"hardware.m4_insert-{i}" for i in range(1, 5)], "color": "#bb9447"}}]
save("07-hardware.json", C)
print("written for L =", L)
