from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
import platform
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = "shhh"

socketio = SocketIO(app)

users_in_room = {}
rooms_sid = {}
names_sid = {}

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/join", methods=["GET"])
def join():
    display_name = request.args.get('display_name') or str(request.remote_addr)
    mute_audio = request.args.get('mute_audio') # 1 or 0
    mute_video = request.args.get('mute_video') # 1 or 0
    room_id = request.args.get('room_id') or str(request.remote_addr)
    session[room_id] = {"name": display_name,
                        "mute_audio": mute_audio, "mute_video": mute_video}
        emit("_log", {'name':display_name,
                      'room':room_id,
                      'sin':sid,
                      "all_users":users_in_room,"all_rooms":rooms_sid,
                     "all_names":names_sid}
             ,room=room_id)
    return render_template("join.html", room_id=room_id, display_name=session[room_id]["name"], mute_audio=session[room_id]["mute_audio"], mute_video=session[room_id]["mute_video"])


@socketio.on("connect")
def on_connect():
    sid = str(request.sid)
    print("New socket connected ", sid)


@socketio.on("join-room")
def on_join_room(data):
    sid = str(request.sid)
    room_id = str(data["room_id"]) or str(request.remote_addr)
    display_name = str(session[room_id]["name"]) or str(request.remote_addr)

    # register sid to the room
    join_room(room_id)
    rooms_sid[sid] = str(room_id)
    names_sid[sid] = str(display_name)

    # broadcast to others in the room
    emit("_log",{'name':display_name,'room':room_id,'sin':sid,"all_users":users_in_room,"all_rooms":rooms_sid,"all_names":names_sid},room=room_id)
    emit("user-connect", {"sid": sid, "name": display_name},
         broadcast=True, include_self=False, room=room_id)

    # add to user list maintained on server
    if room_id not in users_in_room:
        users_in_room[room_id] = list(sid)
        emit("user-list", {"my_id": sid})  # send own id only
    else:
        usrlist = {u_id: names_sid[u_id] 
                       for u_id in users_in_room[room_id]}
        # send list of existing users to the new member
        emit("user-list", {"list": usrlist, "my_id": sid})
        # add new member to user list maintained on server
        users_in_room[room_id].append(sid)
    print("\nusers: ", users_in_room, "\n")


@socketio.on("disconnect")
def on_disconnect():
    sid = str(request.sid)
    room_id = str(rooms_sid[sid]) or str(request.remote_addr)
    display_name = str(names_sid[sid]) or str(request.remote_addr)

    print("[{}] Member left: {}<{}>".format(room_id, display_name, sid))
    emit("user-disconnect", {"sid": sid},
         broadcast=True, include_self=False, room=room_id)

    users_in_room[room_id].remove(sid)
    if len(users_in_room[room_id]) == 0:
        users_in_room.pop(room_id)

    rooms_sid.pop(sid)
    names_sid.pop(sid)

    print("\nusers: ", users_in_room, "\n")


@socketio.on("data")
def on_data(data):
    sender_sid = str(data['sender_id'])
    target_sid = str(data['target_id'])
    if sender_sid != request.sid:
        print("\n[Not supposed to happen!] request.sid and sender_id don't match!!!\n")

    if str(data["type"]) != "new-ice-candidate":
        print('{} message from {} to {}'.format(
            str(data["type"]), sender_sid, target_sid))
    socketio.emit('data', data, room=target_sid)

@app.errorhandler(500)
def server500(e):
#     users_in_room = {}
#     rooms_sid = {}
#     names_sid = {}
    return f"{e.description}<br>{e.message}<br>{users_in_room}"

if __name__=="__main__":
    if any(platform.win32_ver()):
        socketio.run(app, debug=True)

