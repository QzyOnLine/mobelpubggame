import time
import ADBconnect
import screen_scrcpy
import touch
import pubggame.old_rebootgame as old_rebootgame
import gameplayer


def main():
    ADBconnect.main()
    time.sleep(10)
    screen_scrcpy.record_android
    time.sleep(1)
    old_rebootgame.main()
    gameplayer.main()


