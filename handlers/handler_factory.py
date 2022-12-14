"""
Every handler should initialize the `commands` dictionary with the commands it
can handle and the corresponding command class

The handler factory will then check if the handler can process a command,
resolve it and execute it
"""
import shlex

from unidecode import unidecode

from bottypes.invalid_command import InvalidCommand
from util.loghandler import log

handlers = {}
botserver = None


def register(handler_name, handler):
    log.info(
        "Registering new handler: %s (%s)", handler_name, handler.__class__.__name__
    )

    handlers[handler_name] = handler
    handler.handler_name = handler_name


def initialize(slack_wrapper, _botserver, storage_service):
    """
    Initializes all handler with common information.

    Might remove bot_id from here later on?
    """
    global botserver
    botserver = _botserver
    for handler in handlers:
        handlers[handler].init(slack_wrapper, storage_service)


def process(slack_wrapper, storage_service, command, message, timestamp, channel_id, user_id):
    log.debug(
        "Processing message: %s %s from %s (%s)", command, message, user_id, channel_id
    )

    try:  # Parse command and check for malformed input
        command_line = unidecode(" ".join([command, message]))

        lexer = shlex.shlex(command_line, posix=True)
        lexer.quotes = '"'
        lexer.whitespace_split = True

        args = list(lexer)
    except Exception:
        message = "Command failed : Malformed input."
        slack_wrapper.post_message(channel_id, message, timestamp)
        return

    process_command(
        slack_wrapper, storage_service, command, message, args, timestamp, channel_id, user_id
    )


def process_command(
    slack_wrapper,
    storage_service,
    command,
    message,
    args,
    timestamp,
    channel_id,
    user_id,
    admin_override=False,
):

    try:
        handler_name = args[0].lower()
        processed = False
        usage_msg = ""

        admin_users = botserver.get_config_option("admin_users")
        user_is_admin = admin_users and user_id in admin_users

        if admin_override:
            user_is_admin = True
        log.debug(f"Command from admin user: {'True' if user_is_admin else 'False'}")

        # Call a specific handler with this command
        handler = handlers.get(handler_name)

        if handler:
            log.debug(f"Found handler {handler} for {args}")
            # Setup usage message
            if len(args) < 2 or args[1] == "help":
                log.debug(f"Sending usage info")
                usage_msg += handler.get_usage(user_is_admin)
                processed = True

            else:  # Send command to specified handler
                command = args[1].lower()
                if handler.can_handle(command, user_is_admin):
                    log.debug(f"Handler {handler} can handle {args}")
                    handler.process(
                        slack_wrapper,
                        storage_service,
                        command,
                        args[2:],
                        timestamp,
                        channel_id,
                        user_id,
                        user_is_admin,
                    )
                    processed = True
                else:
                    log.debug(f"Handler {handler} can not handle {args}")


        else:  # Pass the command to every available handler
            command = args[0].lower()

            for handler_name, handler in handlers.items():
                if command == "help":  # Setup usage message
                    usage_msg += "{}\n".format(handler.get_usage(user_is_admin))
                    processed = True

                elif handler.can_handle(
                    command, user_is_admin
                ):  # Send command to handler
                    handler.process(
                        slack_wrapper,
                        storage_service,
                        command,
                        args[1:],
                        timestamp,
                        channel_id,
                        user_id,
                        user_is_admin,
                    )
                    processed = True

        if not processed:  # Send error message
            message = "Unknown handler or command : `{}`".format(message)
            slack_wrapper.post_message(channel_id, message, timestamp)

        if usage_msg:  # Send usage message
            send_help_as_dm = botserver.get_config_option("send_help_as_dm") == "1"
            target_id = user_id if send_help_as_dm else channel_id
            slack_wrapper.post_message(target_id, usage_msg)

    except InvalidCommand as e:
        slack_wrapper.post_message(channel_id, str(e), timestamp)

    except Exception:
        log.exception("An error has occured while processing a command")
