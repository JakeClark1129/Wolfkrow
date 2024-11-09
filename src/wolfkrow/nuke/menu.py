
import nuke

menubar = nuke.menu("Nuke")

from wolfkrow import wolfkrow_reload

menu = menubar.addMenu("&Wolfkrow")
menu.addCommand("&Submitter", "import wolfkrow.submitter.nuke_submitter as submitter; submitter.main()")
menu.addCommand("&Reload", "import wolfkrow; wolfkrow_reload(wolfkrow)")

#toolbar = nuke.toolbar("Wolfkrow", True)

