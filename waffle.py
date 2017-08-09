import asyncio
from telepot.aio import Bot
from telepot.aio.loop import MessageLoop
import config
from database import session, User, Waffle, WaffleStatus, Vote

b = Bot(config.token)
l = asyncio.get_event_loop()

async def on_message(msg):
    print("Message received.")
    sender = msg["from"]["id"]
    content = msg.get("text")
    user = session.query(User).filter(User.tid == sender).first()
    if user is None:
        user = User(tid=sender, tusername=msg["from"].get("username"), tfirstname=msg["from"]["first_name"], tlastname=msg["from"].get("last_name"))
        session.add(user)
    if user.waffle is None:
        if content == "/start":
            await user.message(b, "Benvenuto a @SpecialWaffleBot!\n"
                                  "Scrivi /waffle per iniziare.")
        elif content == "/waffle":
            newwaffle = Waffle(status=WaffleStatus.MATCHMAKING)
            session.add(newwaffle)
            session.commit()
            user.join_waffle(b, newwaffle.id)
            session.commit()
            await user.message(b, "Ricerca di altri giocatori in corso...\n"
                                  "Attendi, per piacere!")
    elif user.waffle.status == WaffleStatus.CHATTING:
        if content == "/quit":
            user.vote = Vote.QUIT
            session.commit()
            await user.message(b, "Abbandonerai il Waffle al prossimo round.")
        elif content == "/reveal":
            user.vote = Vote.REVEAL
            session.commit()
            await user.message(b, "Hai votato per rivelare i nomi e concludere il Waffle al prossimo round.")
        elif content == "/expand":
            user.vote = Vote.EXPAND
            session.commit()
            await user.message(b, "Hai votato per espandere il Waffle al prossimo round.")
        elif content == "/votecount":
            message = "I membri del Waffle stanno votando in questo modo:\n"
            for otheruser in user.waffle.users:
                if otheruser.vote is None:
                    message += f"- {otheruser.icon}\n"
                else:
                    message += f"- {otheruser.icon} | {Vote(otheruser.vote).name}\n"
            await user.message(b, message)
    if not content.startswith("/") and user.waffle is not None:
        otherusers = user.waffle.users.copy()
        otherusers.remove(user)
        for otheruser in otherusers:
            l.create_task(otheruser.message(b, f"{user.icon}: {content}"))


async def matchmaking(every):
    while True:
        print("Matchmaking started.")
        waiting = session.query(Waffle).filter(Waffle.status == WaffleStatus.MATCHMAKING).join(User).all()
        waiting.sort(key=lambda w: len(w.users))
        while len(waiting) > 1:
            first = waiting.pop()
            second = waiting.pop()
            message = "Benvenuto al Waffle #{id}!\n" \
                      "Tutti i messaggi che scriverai qui arriveranno agli altri giocatori.\n" \
                      "Ricordati di non rivelare la tua identità, però!" \
                      "Per abbandonare il Waffle, vota /quit.\n" \
                      "Per scoprire il nome degli altri e concludere la partita, vota /reveal.\n" \
                      "Per ingrandire il Waffle, vota /expand.\n" \
                      "La votazione terminerà tra 18 ore. Se non avrai votato niente, verrai espulso per inattività.\n" \
                      "Giocatori in questo Waffle:\n"
            newwaffle = Waffle(status=WaffleStatus.CHATTING)
            session.add(newwaffle)
            session.commit()
            for user in first.users + second.users:
                user.join_waffle(b, newwaffle.id)
                message += f"- {user.icon}\n"
            session.commit()
            session.delete(first)
            session.delete(second)
            session.commit()
            l.create_task(votes(64800, newwaffle.id))
            await newwaffle.message(b, message.format(id=newwaffle.id))
        await asyncio.sleep(every)


async def votes(after, waffle_id):
    await asyncio.sleep(after)
    print(f"Vote counting started for Waffle #{waffle_id}.")
    waffle = session.query(Waffle).filter(Waffle.id == waffle_id).join(User).first()
    vquit, vreveal, vexpand = 0, 0, 0
    for user in waffle.users:
        if user.vote == Vote.QUIT or user.vote is None:
            vquit += 1
            await user.message(b, "Hai abbandonato il Waffle.")
            user.leave_waffle()
            session.commit()
        elif user.vote == Vote.REVEAL:
            vreveal += 1
        elif user.vote == Vote.EXPAND:
            vexpand += 1
    await waffle.message(b, f"La votazione è terminata!\n"
                            f"QUIT: {vquit}\n"
                            f"REVEAL: {vreveal}\n"
                            f"EXPAND: {vexpand}")
    if vquit >= vreveal and vquit >= vexpand:
        await waffle.message(b, "Il Waffle è stato sciolto.")
        session.delete(waffle)
        session.commit()
    elif vreveal >= vexpand:
        message = "Avete deciso di rivelare i nomi utenti!\n"
        for user in waffle.users:
            message += "- {user.icon} era {user}\n"
        message = "Il Waffle è stato sciolto.\n" \
                  "Se vi siete divertiti, create un gruppo normale!"
        await waffle.message(b, message)
        session.delete(waffle)
        session.commit()
    else:
        waffle.status = WaffleStatus.MATCHMAKING
        session.commit()
        await waffle.message(b, "Avete deciso di espandere il Waffle!\n"
                                "Ricerca di altri giocatori in corso...\n"
                                "Attendete, per piacere!")


ml = MessageLoop(b, on_message)
l.create_task(ml.run_forever())
l.create_task(matchmaking(900))
reloading = session.query(Waffle).filter(Waffle.status == WaffleStatus.CHATTING).all()
for waffle in reloading:
    l.create_task(votes(21600, waffle.id))
    l.create_task(waffle.message(b, "Oops! Il bot è stato riavviato e il timer della votazione è ricominciato.\n"
                                    "La votazione finirà tra 6 ore."))
l.run_forever()