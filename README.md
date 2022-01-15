# nicett6

An asyncio based package to talk to a Nice TT6 control unit for tubular motors using the RS-232 protocol

The Nice TT6 control unit is used to control projector screens, garage doors, awnings and blinds.   It is white labelled by Screen Research as the MCS-N-12V-RS232 projector screen controller and by Beamax as the 11299 projector screen controller.

See [this document](https://www.niceforyou.com/sites/default/files/upload/manuals/IS0064A00MM.pdf) for the protocol definition

Known to work with a GANA USB to RS-232 DB9 cable on Windows 10 and on Raspbian Stretch

# Contents

* [Basic Control API](#Basic-Control-API)
* [High Level Cover API](#High-Level-Cover-API)
* [High Level CIW API](#High-Level-CIW-API) (to manage a Constant Image Width configuration with a screen and a mask)
* [Emulator](#Emulator)
* [Examples](#Examples)
* [Notes](#Notes)


# Basic Control API

## Opening a connection

`open_connection([serial_port])`

Opens a connection to the TT6 controlled connected to `serial_port`

If `serial_port` is not supplied or is `None` then an intelligent guess will be made as to the right parameter depending on the platform

The serial_port parameter can be anything that can be passed to `serial.serial_for_url()`.  E.g.

* `/dev/ttyUSB0` (Linux)
* `COM3` (Windows)
* `socket://192.168.0.100:50000` (if you are using a TCP/IP to serial  converter)

Returns an async context managed `MultiPlexerSerialConnection`

Example:

```python
    async with open_connection(serial_port) as conn:
        tt_addr = TTBusDeviceAddress(0x02, 0x04)
        writer = conn.get_writer()
        await writer.send_hex_move_command(tt_addr, 0xE0)
```

## MultiPlexerSerialConnection

A class that allows multiple readers and writers to a single serial connection.

Created by `open_connection([serial_port])`.   See [Opening a connection](#opening-a-connection).

Method|Description
--|--
`MultiPlexerSerialConnection.add_reader()`|Returns a new reader object.<br>If the connection was created by `open_connection` then this will be a `TT6Reader` object, derived from `MultiplexerReader`.<br>The serial connection retains a weak reference to the reader in order to keep it updated.  A reader that is no longer needed can either be dereferenced or explicitly removed.
`MultiPlexerSerialConnection.remove_reader(reader)`|Stops the `reader` object from receiving any further messages
`MultiPlexerSerialConnection.get_writer()`|Returns a new writer object.   If the connection was created by `open_connection` then this will be a `TT6Writer` object, derived from `MultiplexerWriter`.<br>The base class manages contention between multiple potential clients of the same connection.<br>Writer objects do not take any resources and can simply be dereferenced when finished with

## TTBusDeviceAddress

A simple class that represents the address of a TTBus device - to be used for `tt_addr` paramters

Supports comparison with other objects of the same class

Can be used as a key in a mapping type

Property|Description
--|--
`address`|the address of the device on the TTBus
`node`|the device node (usually 0x04)
`as_tuple`|a tuple of `(address, node)`

<br>

Example:

```python
tt_addr = TTBusDeviceAddress(0x02, 0x04)
```

## TT6Reader

A reader that will collect all decoded messages received on the `MultiPlexerSerialConnection` in a queue until it is removed

A `TT6Reader` is an asynchronous iterator returning [response message objects](#Response-message-classes)

Usage:

```python
    async for msg in reader:
        # Do something with msg
```

## Response message classes

### AckResponse

Sent by the controller to acknowledge receipt of a simple command

Property|Description
--|--
`tt_addr`|the `TTBusDeviceAddress` of the TTBus device
`cmd_code`|the command being acknowledged

### HexPosResponse

Sent by the controller in response to a `READ_POS` command

Property|Description
--|--
`tt_addr`|the `TTBusDeviceAddress` of the TTBus device
`cmd_code`|the command being acknowledged
`hex_pos`|the position as a value between 0x00 (fully down/open) and 0xFF (fully up/closed)

### PctPosResponse

Sent by the controller in response to a "web position request"

Property|Description
--|--
`tt_addr`|the `TTBusDeviceAddress` of the TTBus device
`pct_pos`|the position as a value between 0.0 (fully down/open) and 1.0 (fully up/closed)

### InformationalResponse

An informational response from the controller

Typically used to acknowledge a non-device-specific command such as `WEB_ON` or `WEB_OFF`

Property|Description
--|--
`info`|the informational message

### ErrorResponse

An error response from the controller

Property|Description
--|--
`error`|the error message

## TT6Writer

Method|Description
--|--
`TT6Writer.send_web_on()`|Send the WEB_ON command to the controller to enable web commands and to instruct the controller to send the motor positions as they move
`TT6Writer.send_web_off()`|Send the WEB_OFF command to the controller to disable web commands and to instruct the controller not to send the motor positions as they move
`TT6Writer.send_simple_command(tt_addr, cmd_code)`|Send `cmd_code` to the TTBus device at `tt_addr`<br>See the table below for a list of all valid `cmd_code` values
`TT6Writer.send_hex_move_command(tt_addr, hex_pos)`|Instruct the controller to move the TTBus device at `tt_addr` to `hex_pos`<br>`hex_pos` is a value between 0x00 (fully down/open) and 0xFF (fully up/closed)
`TT6Writer.send_web_move_command(tt_addr, pct_pos)`|Instruct the controller to move the TTBus device at `tt_addr` to `pct_pos`<br>`pct_pos` is a value between 0.0 (fully down/open) and 1.0 (fully up/closed)<br>Out of range values for `pct_pos` will be rounded up or down accordingly<br>Web commands must be enabled for this command to work
`TT6Writer.send_web_pos_request(tt_addr)`|Send a request to the controller to send the position of the TTBus device at `tt_addr`<br>Web commands must be enabled for this command to work
`TT6Writer.process_request(coro, [time_window])`|Send a command and collect the response messages that arrive in time_window

<br>Command codes for `send_simple_command`:

Code|Meaning
--|--
`READ_POS`|Request the current position<br>Controller will send a value between 0x00 (fully down/open) and 0xFF (fully up/closed) 
`STOP`|Stop
`MOVE_DOWN`|Move down
`MOVE_UP`|Move up
`MOVE_POS_<n>`|Move to preset `n` where `n` is between 1 and 6
`STORE_POS_<n>`|Store current position to preset `n` where `n` is between 1 and 6
`DEL_POS_<n>`|Clear preset `n` where `n` is between 1 and 6
`MOVE_DOWN_STEP`|Move down the smallest possible step (web pos is not reported by controller)
`MOVE_UP_STEP`|Move up the smallest possible step (web pos is not reported by controller)
`STORE_UPPER_LIMIT`|Store current position to upper limit (BEWARE!)
`STORE_LOWER_LIMIT`|Store current position to lower limit (BEWARE!)
`DEL_UPPER_LIMIT`|Clear upper limit (BEWARE!)
`DEL_LOWER_LIMIT`|Clear lower limit (BEWARE!)

<br>Usage:

```python
    writer = conn.get_writer()
    writer.send_web_move_command(1.0)
```

Usage of `process_request()`:

```python
    coro = writer.send_simple_command(tt_addr, "READ_POS")
    messages = await writer.process_request(coro)
```

Note that there could be unrelated messages received if web commands are enabled or if another command has just been submitted

# High level Cover API

A set of components to provide a high level interface to manage a Cover.    Could be used to control a retractable projector screen or a garage door.  Designed for use with Home Assistant.

Component|Description
--|--
`CoverManager`|A class that manages the controller connection and a set of covers<br>Can be used as an async context manager
`Cover`|A sensor class that can be used to monitor the position of a cover
`TT6Cover`|Class that sends commands to a `Cover` that is connected to the TTBus
`PostMovementNotifier`|Helper class that resets a cover to idle after movement has stopped

<br>Example (also see [example3.py](#Examples) below):

```python
async def log_cover_state(cover):
    try:
        while cover.is_moving:
            _LOGGER.info(
                f"drop: {cover.drop}; "
                f"is_opening: {cover.is_opening}; "
                f"is_closing: {cover.is_closing}; "
            )
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass

async def example(serial_port):
    tt_addr = TTBusDeviceAddress(0x02, 0x04)
    max_drop = 2.0
    async with CoverManager(serial_port) as mgr:
        tt6_cover = await mgr.add_cover(tt_addr, Cover("Cover", max_drop))

        message_tracker_task = asyncio.create_task(mgr.message_tracker())
        logger_task = asyncio.create_task(log_cover_state(tt6_cover.cover))

        await tt6_cover.send_drop_pct_command(0.9)
        await wait_for_motion_to_complete([tt6_cover.cover])

        await tt6_cover.send_close_command()
        await wait_for_motion_to_complete([tt6_cover.cover])

        logger_task.cancel()
        await logger_task

    await message_tracker_task
```

## CoverManager

A class that manages the connection and a set of covers

Can be used as an async context manager

Constructor parameters:

Parameter|Description
--|--
`serial_port`|The serial port to use.  See [Opening a connection](#opening-a-connection) for the valid values.

Property|Description
--|--
`serial_port`|The serial port in use
`tt6_covers`|All of the `TT6Cover` objects that have been added (the returned object is a `ValuesView` onto the internal dict)

Method|Description
--|--
`CoverManager.open()`|Open the connection<br>Called automatically if the object is used as a context manager
`CoverManager.close()`|Close the connection<br>Called automatically if the object is used as a context manager
`CoverManager.add_cover(tt_addr, cover)`|Add a cover to be managed<br>tt_addr is the TTBus address of the cover<br>The connection must be open so that the initial position can be requested
`CoverManager.message_tracker()`|A coroutine that must be running in the background for the manager to be able to track cover positions

## Cover

A sensor class that can be used to monitor the position of a cover.  Could be used to monitor a retractable projector screen or a garage door.  Designed for use with Home Assistant.

Cover is an `AsyncObservable` and will notify any attached objects of type `AsyncObserver` if the `drop_pct` is changed

Constructor parameters:

Parameter|Description
--|--
`name`|name of cover (for logging purposes)
`max_drop`|maximum drop of cover in metres

<br>
Example:

```python
cover = Cover("Screen", 2.0)
```

<br>
Has the following properties and methods:

Property|Description
--|--
`Cover.drop_pct`|the percentage drop (0.0 = fully open/down, 1.0 = fully closed/up)
`Cover.drop`|drop in metres
`Cover.is_moving`|returns True if the cover has moved recently
`Cover.is_closed`|returns True if the cover is fully up (opposite of a blind)
`Cover.is_closing`|returns True if the cover is going up (opposite of a blind)<br>will only be meaningful after `drop_pct` has been set by the first POS message coming back from the cover for a movement
`Cover.is_opening`|returns True if the cover is going down (opposite of a blind)<br>will only be meaningful after `drop_pct` has been set by the first POS message coming back from the cover for a movement


Method|Description
--|--
`Cover.set_drop_pct`|Set the percentage drop (0.0 = fully open/down, 1.0 = fully closed/up) - async<br>Will notify observers of the state change
`Cover.moved()`|Called to indicate movement<br>When initiating movement, call `moved()` so that `is_moving` will be meaningful in the interval before the first POS message comes back from the cover<br>Will notify observers of the state change
`Cover.set_idle()`|Called to indicate that the cover is idle<br>After detecting that the cover is idle, call `set_idle()` so that the next movement direction will be correctly inferred<br>Will notify observers of the state change
`Cover.check_for_idle()`|Called to check whether movement has ceased<br>Returns True if the cover is idle<br>Will invoke Cover.set_idle() if the cover became idle since the last call

Helper|Description
--|--
`wait_for_motion_to_complete(covers)`|Waits for motion of a list of covers to complete<br>Has side effect of notifying observers of the cover when it goes idle


## TT6Cover

Class that sends commands to a `Cover` that is connected to the TTBus

Intended to be constructed by `CoverManager.add_cover()`

Property|Description
--|--
`TT6Cover.tt_addr`|the TTBus address of the Cover
`TT6Cover.cover`|the `Cover` helper
`TT6Cover.writer`|the low level `TT6Writer`

Method|Description
--|--
`TT6Cover.send_pos_request()`|Send a POS request to the controller
`TT6Cover.send_drop_pct_command(drop_pct)`|Send a POS command to the controller to set the drop percentage of the Cover to `drop_pct`<br>`drop_pct` should be between 0.0 (fully open/down) and 1.0 (fully closed/up)<br>Out of range values for `drop_pct` will be rounded up/down accordingly
`TT6Cover.send_close_command()`|Send a close command to the controller for the Cover
`TT6Cover.send_open_command()`|Send an open command to the controller for the Cover
`TT6Cover.send_preset_command(preset_num)`|Send an preset command to the controller for the Cover
`TT6Cover.send_stop_command()`|Send a stop command to the controller for the Cover

## PostMovementNotifier

Helper class that resets a cover to idle after movement has stopped

Documented here for completeness but intended to be constructed by and internal to the `CoverManager`

Most state changes of a `Cover` will be triggered by the receipt of a POS message.  The `Cover` infers that there is movement when a message is received and infers the direction from the current and previous message.   However, there is no notification that the `Cover` is idle so the `PostMovementNotifier` class detects that there has been no movement for a period and then calls `Cover.set_idle()`.  The `Cover` will then notify its observers that it is idle.

The class implements the `AsyncObserver` interface and is intended to be attached to a `Cover`.  Whenever the `Cover` moves it calls `notifyObservers()` which calls `PostMovementNotifier.update()`.  A task is created that will wait for a period and then set the `Cover` to idle.   If a task was already running when the movement notification is received then the task will be cancelled and restarted.

The task must sleep for `Cover.MOVEMENT_THRESHOLD_INTERVAL + PostMovementNotifier.POST_MOVEMENT_ALLOWANCE` seconds without being cancelled for the `Cover` to be considered idle.


# High level CIW API

A high level API to manage a Constant Image Width retractable projector screen with a mask

Component|Description
--|--
`CIWManager`|A class that manages a screen and mask simultaneously
`CIWHelper`|A sensor class that tracks the positions of a screen and mask<br>Has properties to represent the visible image area<br>Provides methods to calculate the drops needed for a specific aspect ratio
`ImageDef`|A class that describes where the image area is located on a cover that is a screen

<br>Example (also see [example1.py](#Examples) below):

```python
async def main(serial_port=None):
    async with CoverManager(serial_port) as mgr:
        screen_tt6_cover = await mgr.add_cover(
            TTBusDeviceAddress(0x02, 0x04), Cover("Screen", 1.77)
        )
        mask_tt6_cover = await mgr.add_cover(
            TTBusDeviceAddress(0x03, 0x04), Cover("Mask", 0.6)
        )
        ciw = CIWManager(
            screen_tt6_cover,
            mask_tt6_cover,
            ImageDef(0.05, 1.57, 16 / 9),
        )
        reader_task = asyncio.create_task(mgr.message_tracker())
        mode = CIWAspectRatioMode.FIXED_BOTTOM
        baseline_drop = ciw.default_baseline_drop(mode)
        await ciw.send_set_aspect_ratio(2.35, mode, baseline_drop)
        await ciw.wait_for_motion_to_complete()
    await reader_task
```

## CIWManager

A class that manages a screen and mask simultaneously

Constructor parameters:

Parameter|Description
--|--
`screen_tt6_cover`|The `TT6Cover` through which the screen cover can be controlled
`mask_tt6_cover`|The `TT6Cover` through which the mask cover can be controlled
`image_def`|An ImageDef object describing where the image area on the screen cover is

Property|Description
--|--
`CIWManager.screen_tt6_cover`|The `TT6Cover` through which the screen cover can be controlled
`CIWManager.mask_tt6_cover`|The `TT6Cover` through which the mask cover can be controlled
`CIWManager.image_def`|An ImageDef object describing where the image area on the screen cover is

Method|Description
--|--
`CIWManager.get_helper()`|Return a `CIWHelper` sensor object referencing the `Cover` sensor objects referenced by the screen and mask `TT6Cover` objects
`CIWManager.send_pos_request()`|Send a POS request to the screen and mask
`CIWManager.send_close_command()`|Send a close command to the screen and mask
`CIWManager.send_open_command()`|Send an open command to the screen and mask
`CIWManager.send_stop_command()`|Send a stop command to the screen and mask
`CIWManager.send_set_aspect_ratio(target_aspect_ratio, mode, baseline_drop)`|Send commands to set a specific aspect ratio<br>See `CIWManager.calculate_new_drops` for more details
`CIWManager.wait_for_motion_to_complete()`|Waits for motion to complete for both screen and mask<br>Has side effect of notifying observers of the cover when it goes idle
`CIWManager.calculate_new_drops(target_aspect_ratio, mode, baseline_drop`)|Calculate the screen and mask drops necessary to set the `target_aspect_ratio`<br>`mode` defines whether the position of the top, middle or bottom of the screen should be held constant relative to `baseline_drop`<br>(See [CIWAspectRatioMode](#CIWApectRatioMode) for details)<br>Returns `None` if the `target_aspect_ratio` can't be achieved
`CIWManager.default_baseline_drop(mode)`|Return the most useful baseline_drop for each mode, e.g. with the screen fully extended


## CIWApectRatioMode

An enumeration used to specify where the target visible image area should be relative to the current visible image area

Enum Value|Description
--|--
CIWApectRatioMode.FIXED_TOP|The top of the current visible area is fixed<br>Typically the mask stays where it is and the screen moves up and down<br>If the mask is fully up then it will move to the top of the current image area
CIWApectRatioMode.FIXED_MIDDLE|The middle line of the current visible area is fixed<br>Both the screen and mask will move
CIWApectRatioMode.FIXED_BOTTOM|The middle line of the current visible area is fixed<br>Typically the screen stays where it is and the mask moves up and down


## CIWHelper

A sensor class that represents the positions of a screen and mask

Constructor parameters:

Parameter|Description
--|--
`screen`|A `Cover` sensor object representing the screen
`mask`|A `Cover` sensor object representing the mask
`image_def`|An ImageDef object describing where the image area on the screen cover is

Properties:

Property|Description
--|--
`CIWHelper.image_width`|the width of the visible image in metres
`CIWHelper.image_height`|the height of the visible image in metres or `None` if the image is not visible
`CIWHelper.image_diagonal`|the diagonal of the visible image in metres or `None` if the image is not visible
`CIWHelper.image_area`|the area of the visible image in square metres or `None` if the image is not visible
`CIWHelper.image_is_visible`|True if the image area is visible or `None` if the image is not visible
`CIWHelper.aspect_ratio`|The aspect ratio of the visible image or `None` if the image is not visible

## ImageDef

A class that describes where the image area is located on a cover that is a screen

Constructor parameters:

Parameter|Description
--|--
`bottom_border_height`|gap in metres between bottom of image and bottom of cover
`height`|height of image
`aspect_ratio`|aspect ratio of image

<br>
Example:

```python
image_def = ImageDef(0.05, 2.0, 16 / 9)
```

<br>Has the following properties and methods:

Property|Description
--|--
`ImageDef.width`|implied image width


Method|Description
--|--
`ImageDef.implied_image_height(target_aspect_ratio)`|implied height for `target_aspect_ratio` if the width is held constant
<br>

# Emulator

The package also includes an emulator that can be used for demonstration or testing purposes

Example:

```
python -m nicett6.emulator
```

Usage:

```
usage: python -m nicett6.emulator [-h] [-f FILENAME] [-p PORT] [-w] [-W]
                   [-i cover_name percentage]

optional arguments:
  -h, --help            show this help message and exit
  -f FILENAME, --filename FILENAME
                        config filename
  -p PORT, --port PORT  port to serve on
  -w, --web_on          emulator starts up in web_on mode
  -W, --web_off         emulator starts up in web_off mode
  -i cover_name percentage, --initial_pos cover_name percentage
                        override the initial percentage position for cover
```

A sample `config.json` file is provided in the `emulator/config` folder

Sample config:

```json
{
    "web_on": false,
    "covers": [
        {
            "address": 2,
            "node": 4,
            "name": "screen",
            "step_len": 0.01,
            "max_drop": 1.77,
            "speed": 0.08
        },
        {
            "address": 3,
            "node": 4,
            "name": "mask",
            "step_len": 0.01,
            "max_drop": 0.6,
            "speed": 0.08
        }
    ]
}
```

# Examples

The following examples can be used in conjunction with the [Emulator](#Emulator)

* `example1.py` - shows how to use the [High Level CIW API](#High-Level-CIW-API)
* `example2.py` - shows how to use the [Basic Control API](#Basic-Control-API)
* `example3.py` - shows how to use the [High Level Cover API](#High-Level-Cover-API)

# Utilities

## Movement Timing Logger

The script `movement_timing_logger.py` can be used to see how often the controller publishes POS messages as it moves.   It will move the specified Cover down and then back up and log the time between messages.   This can be used to tune `Cover.MOVEMENT_THRESHOLD_INTERVAL` so that `Cover.is_moving` is accurate.

```
usage: movement_timing_logger.py [-h] [-s SERIAL_PORT] [-a {2,3}]

optional arguments:
  -h, --help            show this help message and exit
  -s SERIAL_PORT, --serial_port SERIAL_PORT
                        serial port
  -a {2,3}, --address {2,3}
                        device address
```

# Notes

## End of Line (EOL) characters

The protocol definition specifies that all messages end in a carriage return character but in practice the controller seems to use carriage return plus line feed.

For convenience the API can handle either.

* The API will write to the controller with messages ending in carriage return
* The API will handle messages from the controller with either line ending
* The emulator will handle inbound commands with either line ending
* The emulator will send responses ending in carriage return and line feed

## Measurement units

This document refers to metres as the unit of measurement for all absolute measurements but you can use mm, cm, inches or feet as long as you are consistent
