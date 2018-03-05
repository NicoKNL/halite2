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

# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
game = hlt.Game("Settler")
# Then we print our start message to the logs
logging.info("Starting my Settler bot!")

# Some constants
STARTING_TURNS = 2

while True:
    # TURN START
    # Update the map for the new turn and get the latest version
    game_map = game.update_map()
    me = game_map.get_me()
    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    command_queue = []
    planned_planets = []

    # Info about the planets
    owned_planets = [p for p in game_map.all_planets() if p.is_owned() and p.owner == me]
    enemy_planets = [p for p in game_map.all_planets() if p.is_owned() and p.owner != me]
    empty_planets = [p for p in game_map.all_planets() if p.is_owned() == False]
    full_planets = [p for p in game_map.all_planets() if p.is_full()]

    # For every ship that I control
    my_ships = game_map.get_me().all_ships()
    for i, ship in enumerate(my_ships):

        ### START OF GAME LOGIC ###
        if STARTING_TURNS > 0:
            STARTING_TURNS -= 1

            direction = 0

            # Fanning out logic
            for s in my_ships:
                if s.id != ship.id:
                    direction += (ship.calculate_angle_between(s) + 180) % 360

            direction = direction / 2.0

            navigate_command = ship.thrust(hlt.constants.MAX_SPEED, direction)
            command_queue.append(navigate_command)
            continue

        ### MAIN GAME LOGIC ###

        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            continue  # Skip this ship

        closest_planet = None
        ship_will_start_docking = False

        if len(empty_planets) > 0:
            for planet in empty_planets:
                if ship_will_start_docking:
                    continue

                # If the ship CAN dock
                if ship.can_dock(planet):
                    # We add the command by appending it to the command_queue
                    ship_will_start_docking = True
                    command_queue.append(ship.dock(planet))
                else:

                    if closest_planet is None and planet not in full_planets:
                        closest_planet = planet

                    else:
                        logging.info("----------------------------------------------")
                        logging.info(str(ship.calculate_distance_between(planet)) + "  vs  " + str(
                            ship.calculate_distance_between(closest_planet)))
                        logging.info("----------------------------------------------")

                        if ship.calculate_distance_between(planet) < ship.calculate_distance_between(closest_planet):
                            closest_planet = planet

            if closest_planet and not ship_will_start_docking:
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=False)
                if navigate_command:
                    command_queue.append(navigate_command)
            continue

        elif len(enemy_planets) > 0:
            for planet in enemy_planets:
                if closest_planet is None and planet not in full_planets:
                    closest_planet = planet

                else:
                    logging.info("----------------------------------------------")
                    logging.info(str(ship.calculate_distance_between(planet)) + "  vs  " + str(
                        ship.calculate_distance_between(closest_planet)))
                    logging.info("----------------------------------------------")

                    if ship.calculate_distance_between(planet) < ship.calculate_distance_between(closest_planet):
                        closest_planet = planet

            if closest_planet:
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=True)
                if navigate_command:
                    command_queue.append(navigate_command)
            continue
            #
            #
            #
            #
            # #
            # # current_target_planet_distance = -1
            # #
            # # # For each planet in the game (only non-destroyed planets are included)
            # for planet in game_map.all_planets():
            #     # If the planet is owned
            #     if planet.is_owned():
            #         # Skip this planet
            #         continue
            # #
            #     # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
            #     if ship.can_dock(planet):
            #         # We add the command by appending it to the command_queue
            #         command_queue.append(ship.dock(planet))
            #     else:
            #         if planet in planned_planets:
            #             continue
            #         else:
            #             if ship.calculate_distance_between(planet) < current_target_planet_distance or current_target_planet_distance == -1:
            #                 # If we can't dock, we move towards the closest empty point near this planet (by using closest_point_to)
            #                 # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
            #                 # We run this navigate command each turn until we arrive to get the latest move.
            #                 # Here we move at half our maximum speed to better control the ships
            #                 # In order to execute faster we also choose to ignore ship collision calculations during navigation.
            #                 # This will mean that you have a higher probability of crashing into ships, but it also means you will
            #                 # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
            #                 # wish to turn that option off.
            #                 navigate_command = ship.navigate(
            #                     ship.closest_point_to(planet),
            #                     game_map,
            #                     speed=int(hlt.constants.MAX_SPEED),  # / 2
            #                     ignore_ships=False)
            #                 # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
            #                 # or we are trapped (or we reached our destination!), navigate_command will return null;
            #                 # don't fret though, we can run the command again the next turn)
            #                 if navigate_command:
            #                     if current_target_planet_distance != -1:
            #                         command_queue.pop(-1)
            #                     command_queue.append(navigate_command)
            #                     planned_planets.append(planet)
            #                     current_target_planet_distance = ship.calculate_distance_between(planet)
            #     break

    # Sanitize the command queue, we check for double commands and we keep the first one for each ship
    c_tracker = []
    clean_command_queue = []
    for c in command_queue:
        c_ship = c.split(" ")[1]
        if c in c_tracker:
            continue
        else:
            c_tracker.append(c)
            clean_command_queue.append(c)

    # Send our set of commands to the Halite engine for this turn
    logging.info(clean_command_queue)
    game.send_command_queue(clean_command_queue)
    # TURN END
# GAME END
