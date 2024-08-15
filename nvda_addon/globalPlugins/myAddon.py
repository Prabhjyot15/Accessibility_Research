import globalPluginHandler
import api

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def report_focus(self):
        # Retrieve the current focus object
        focus_obj = api.getFocusObject()

        # Retrieve information about the object
        name = focus_obj.name
        role = focus_obj.roleText
        state = ", ".join(focus_obj.states)

        # Construct the message
        message = f"Focus: {name}, Role: {role}, State: {state}"
        return message
