"""
Welcome to your first Halite-II bot!

This bot's name is Settler. It's purpose is simple (don't expect it to win complex games :) ):
1. Initialize game
2. If a ship is not docked and there are unowned planets
2.a. Try to Dock in the planet if close enough
2.b If not, go towards the planet

Note: Please do not place print statements here as they are used to communicate with the Halite engine. If you need
to log anything use the logging module.
"""
# Let's start by importing the Halite Starter Kit so we can interface with the Halite engine
import hlt
# Then let's import the logging module so we can print out information
import logging


def closest_entity(ship, entities, exclusions=[], max_distance=15, depth=0):
    closest = False
    valid_entities = [e for e in entities if e not in exclusions]
    for e in valid_entities:
        distance = ship.calculate_distance_between(e)
        if not closest and distance < max_distance:
            closest = e
        elif closest:
            if distance < ship.calculate_distance_between(closest):  # optimize b in (a < b)
                closest = e
        else:
            continue

    if closest:
        return closest
    elif depth > 2:
        return None
    else:
        return closest_entity(ship, entities, exclusions=exclusions, max_distance=max_distance*2, depth=depth + 1)


# GAME START
game = hlt.Game("Main3")
logging.info("Starting my Settler bot!")
TURN = 0

while True:
    TURN += 1
    # TURN START
    # Update the map for the new turn and get the latest version
    game_map = game.update_map()
    me = game_map.get_me()
    command_queue = []  # Here we define the set of commands to be sent to the Halite engine at the end of the turn

    # Info about the fleet
    owned_ships = me.all_ships()
    # docked_ships = [s for s in owned_ships if s.docking_status == s.DockingStatus.DOCKED]
    free_ships = [s for s in owned_ships if s.docking_status == s.DockingStatus.UNDOCKED]
    enemy_ships = [s for s in game_map._all_ships() if s not in owned_ships]

    # logging.info(f"enemy ships: {enemy_ships}")

    # Info about the planets
    owned_planets = [p for p in game_map.all_planets() if p.is_owned() and p.owner == me]
    enemy_planets = [p for p in game_map.all_planets() if p.is_owned() and p.owner != me]
    empty_planets = [p for p in game_map.all_planets() if p.is_owned() == False]
    full_planets = [p for p in game_map.all_planets() if p.is_full()]

    ### START OF GAME LOGIC ###
    if TURN < 2:
        direction = 0

        # Fanning out logic
        for ship in free_ships:
            for other_ship in free_ships:
                if ship.id != other_ship.id:
                    direction += (ship.calculate_angle_between(other_ship) + 180) % 360

            direction = direction / 2.0
            docking = False
            for planet in empty_planets:
                if ship.can_dock(planet):
                    # We add the command by appending it to the command_queue
                    command_queue.append(ship.dock(planet))
                    docking = True
                    break
            if not docking:
                navigate_command = ship.thrust(hlt.constants.MAX_SPEED, direction)
                command_queue.append(navigate_command)

        game.send_command_queue(command_queue)
        continue


    ### EARLY GAME LOGIC ###
    if TURN < 25:
        direction = 0

        # Fanning out logic
        for i, ship in enumerate(free_ships):
            i *= 2
            while (i > len(empty_planets)):
                i -= 1

            if ship.can_dock(empty_planets[i]):
                command_queue.append(ship.dock(empty_planets[i]))
            else:
                navigate_command = ship.navigate(ship.closest_point_to(empty_planets[i]),
                                                 game_map,
                                                 speed=int(hlt.constants.MAX_SPEED))
                command_queue.append(navigate_command)
            # direction = 360 / len(free_ships) * float(i)
            #
            # # direction = direction / 2.0
            # docking = False
            # for planet in empty_planets:
            #     if ship.can_dock(planet):
            #         # We add the command by appending it to the command_queue
            #         command_queue.append(ship.dock(planet))
            #         docking = True
            #         break
            # if not docking:
            #     navigate_command = ship.thrust(hlt.constants.MAX_SPEED, direction)
            #     command_queue.append(navigate_command)

        game.send_command_queue(command_queue)
        continue

    ### MAIN GAME LOGIC ###
    # For every ship that I control
    for ship in free_ships:
        # Basic stuff, probably dict.
        navigate_command = None
        target_type = "planet"  # probably move to dictionary and build it to contain current tasks etc..

        ## Decision logic (which target) ##
        # Closest non-full planet I currently own
        closest_target = closest_entity(ship, owned_planets, exclusions=full_planets)  # max distance preferable

        if not closest_target:  # Closest non-empty planet that my ship could start to populate
            closest_target = closest_entity(ship, empty_planets)

        if not closest_target:  # Closest enemy my ship could attack
            closest_target = closest_entity(ship, enemy_ships)
            # logging.info(f"closest_enemy: {closest_target}")
            target_type = "enemy_ship"

        if not closest_target:  # No closest target found...
            # logging.info(f"no closest target found. - {type(closest_target)}")
            target_type = None

        # Act upon the target if it's there
        if target_type:
            if target_type == "planet":
                if ship.can_dock(closest_target):
                    # We add the command by appending it to the command_queue
                    command_queue.append(ship.dock(closest_target))
                    continue

                navigate_command = ship.navigate(
                    ship.closest_point_to(closest_target),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=False)

            elif target_type == "enemy_ship":
                # logging.info(f"targeting ship @ {closest_target}")
                navigate_command = ship.navigate(
                    closest_target,  # not the closest point to
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=True)
                # logging.info(f"{navigate_command}")

        if navigate_command:
            # logging.info(f"adding to queue: {navigate_command}")
            command_queue.append(navigate_command)
        else:
            closest_target = closest_entity(ship, enemy_ships, max_distance=50)
            navigate_command = ship.navigate(
                ship.closest_point_to(closest_target),
                game_map,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=False)
            # logging.info("no closest planet")
            pass

    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END
# GAME END
