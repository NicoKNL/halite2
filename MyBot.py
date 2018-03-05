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
import math
# Then let's import the logging module so we can print out information
import logging
import random
from collections import OrderedDict

NAV_CORRECTIONS = 6
NAV_ANGLE_STEP = 15


class CommandCenter(object):
    def __init__(self, game):
        self.game = game
        self.game_map = None
        self.me = None

        self.units = []
        self.targeted_planets = {}
        self.targeted_enemy_ships = {}

        self.owned_ships = None
        self.all_planets = None
        self.owned_planets = None
        self.enemy_planets = None
        self.empty_planets = None
        self.full_planets = None

        self.early_hunters = 0

        self.turn = 0

    def next_move(self):
        self.turn += 1
        self.game_map = self.game.update_map()
        self.me = self.game_map.get_me()
        self.owned_ships = self.me.all_ships()

        # # logging.info(":: updating map data ::")
        self.update_map_data()

        # # logging.info(":: updating units")
        self.update_units()
        # # logging.info(f"units: {len(self.units)} - {self.units}")
        # # logging.info(":: determining tasks")
        self.determine_tasks()
        # # logging.info(f"tasks: {[(u.get_ship(), u.get_task()) for u in self.units]}")
        # # logging.info(":: -------------- executing tasks")
        self.execute_tasks()
        # # logging.info(f"-----active targets: {self.targeted_planets}")

    def update_units(self):
        # # logging.info(f"owned_ships: {len(self.owned_ships)} - {self.owned_ships}")

        updated_units = []
        # Remove ships that have died
        for unit in self.units:
            # # logging.info(f"start compare: {unit.get_ship()} - {[s.id for s in self.owned_ships]}")
            if unit.get_ship() in [s.id for s in self.owned_ships]:
                # # logging.info(f"    still alive: {unit.get_ship()}")
                updated_units.append(unit)
            else: # unit died
                self.update_targeted_planets(unit, None)
                # else:
                # # logging.info(f"    unit died: {unit.get_ship()}")
                # self.units.pop(i)
                # Remove it's targets from the targetlist
                # if unit.target in self.targeted_planets.keys():
                #     self.targeted_planets[unit.target] -= 1

        self.units = updated_units
        # # logging.info(f"unit_check A: {len(self.units)} - {[(unit.get_ship(), unit) for unit in self.units]}")

        # Add new ships that are not yet in the log
        for ship in self.owned_ships:
            if ship.id not in [u.get_ship() for u in self.units]:
                # # logging.info(f"    Adding: {ship.id}")
                new_unit = Unit(ship.id)
                self.units.append(new_unit)

        # # logging.info(f"unit_check B: {len(self.units)} - {[(unit.get_ship(), unit) for unit in self.units]}")

    def update_map_data(self):
        self.all_planets = self.game_map.all_planets()
        self.owned_ships = self.me.all_ships()
        self.enemy_ships = [s for s in self.game_map._all_ships() if s.owner != self.me]
        self.owned_planets = [p for p in self.game_map.all_planets() if p.is_owned() and p.owner == self.me]
        self.enemy_planets = [p for p in self.game_map.all_planets() if p.is_owned() and p.owner != self.me]
        self.empty_planets = [p for p in self.game_map.all_planets() if len(p.all_docked_ships()) == 0]
        self.full_planets = [p for p in self.game_map.all_planets() if p.is_full()]

    def update_targeted_planets(self, unit, planet):
        previous_target = unit.get_target(self.game_map)
        if (previous_target != None) and (previous_target.id in self.targeted_planets.keys()):
            self.targeted_planets[previous_target.id] -= 1
            # logging.info(f"SUBTRACTING, new value {self.targeted_planets[previous_target.id]}")
        elif planet:
            unit.set_target(planet)
            if planet.id in self.targeted_planets.keys():
                self.targeted_planets[planet.id] += 1
                # logging.info(f"ADDING, new value {self.targeted_planets[planet.id]}")
            else:
                self.targeted_planets[planet.id] = 1
                # logging.info(f"KEY NOT FOUND, SETTING, new value {self.targeted_planets[planet.id]}")
        else:
            pass

    def determine_threats(self, threat_distance=50):
        threats = {}
        for planet in self.owned_planets:
            for ship in self.enemy_ships:
                distance = planet.calculate_distance_between(ship)
                if distance <= threat_distance:
                    if planet.id not in threats.keys():
                        threats[planet.id] = [ship.id]
                    else:
                        threats[planet.id].append(ship.id)
        return threats

    def determine_defender_candidates(self, threat_distance=50):
        candidates = {}
        for planet in self.owned_planets:
            for ship in self.owned_ships:
                distance = planet.calculate_distance_between(ship)
                if distance <= threat_distance:
                    if planet.id not in candidates.keys():
                        candidates[planet.id] = [ship.id]
                    else:
                        candidates[planet.id].append(ship.id)
        return candidates

    def determine_tasks(self):
        testing = False

        threats = self.determine_threats(threat_distance=20)
        defender_candidates = self.determine_defender_candidates(threat_distance=70)
        # logging.info(f"Threats: {threats}")
        # logging.info(f"Defender_candidates: {defender_candidates}")

        for unit in self.units:
            ship = ship_by_id(self.owned_ships, unit.get_ship())
            current_task = unit.get_task()
            # # logging.info(f"previously: {unit.get_ship()} - {unit.get_age()} - {current_task}")
            # # logging.info("[1]")
            if testing == True:  # To test develop and test behaviour #
                unit.set_task("corner_rat")
                continue

            if current_task == "stay_docked":
                if ship.docking_status is hlt.entity.Ship.DockingStatus.DOCKED:
                    continue

            if current_task == "corner_rat":
                # # logging.info("[2A] staying docked")
                continue

            if unit.get_age() == 0:
                coinflip = random.random()
                if coinflip > 0.5:
                    will_dock = False
                    for p in self.all_planets:
                        if ship.can_dock(p) and p not in self.enemy_planets and not p.is_full():
                            unit.set_target(p)
                            unit.set_task("collonize_planet")
                            will_dock = True
                    if will_dock:
                        continue

                # # logging.info("[2B] ---> avoid danger!! <---")
                unit.set_task("avoid_danger")
                continue

            # no planets anymore but we have ships and there are empty planest. GOGOGO!
            if len(self.owned_planets) == 0 and len(self.empty_planets) > 0:
                planets_by_distance = list(sort_entities_by_distance(ship, self.empty_planets).items())
                # # logging.info(f"planets by distance: {planets_by_distance}")
                # i = 0
                if planets_by_distance:
                    unit.set_task("collonize_planet")
                    target = planets_by_distance[0][0]
                    self.update_targeted_planets(unit, target)
                    continue

            # logging.info(f"early hunter testA: {(len(self.owned_ships) > 3)} - {(self.turn < 50)} - {(self.early_hunters < 2)}")
            # logging.info(f"early hunter testB: {(len(self.owned_ships) > 3) and (self.turn < 50) and (self.early_hunters < 2)}")
            if ((len(self.owned_ships) > 3) and (self.turn < 50) and (self.early_hunters < 2)) or current_task == "hunter":
                # logging.info(f"------------assigning hunter: {ship.id}")
                if current_task != "hunter":
                    self.early_hunters += 1
                closest_docked_enemy_ship = closest_entity(ship, [s for s in self.enemy_ships if s.docking_status is hlt.entity.Ship.DockingStatus.DOCKED], max_distance=100)
                # logging.info(f"------closest_enemy_ship: {closest_docked_enemy_ship}")
                if closest_docked_enemy_ship:
                    unit.set_target(closest_docked_enemy_ship)
                    unit.set_task("hunter")
                else:
                    unit.set_target(None)
                    unit.set_task("hunter")
                # whilst NOT close to the specific docked ship, increase the radius perhaps to avoid enemies
                continue


            # Defense calculation
            bolster_defense = False
            for planet in threats.keys():
                if len(threats[planet]) > 0:
                    if ship.id in defender_candidates[planet]:
                        unit.set_task("defender")
                        unit.set_target(ship_by_id(self.enemy_ships, threats[planet][0]))
                        bolster_defense = True
                        break

            if bolster_defense:
                continue


            if current_task == "collonize_planet":
                continue


            # logging.info(f"empty_planets: {self.empty_planets}")
            # logging.info(f"targets: {self.targeted_planets}")
            if (len(self.empty_planets) > 0) and (current_task not in ["hunter", "defender"]):
                unit.set_task("collonize_planet")
                # # logging.info("[2C] updating task to collonization!!!")
                planets_by_distance = list(sort_entities_by_distance(ship, self.empty_planets).items())
                # # logging.info(f"planets by distance: {planets_by_distance}")
                # i = 0
                if planets_by_distance:
                    target = planets_by_distance[0][0]
                    self.update_targeted_planets(unit, target)
                    continue
                    # for planet, distance in planets_by_distance:
                    #     # logging.info(f"planet: {planet.id} - in targets: {(planet.id in self.targeted_planets.keys())}")
                    #     if planet.id in self.targeted_planets.keys():
                    #         if self.targeted_planets[planet.id] > 0:
                    #             continue
                    #     else:
                    #         target = planet
                    #         self.update_targeted_planets(unit, target)
                    #
                    # if not unit.get_target(self.game_map):
                    #     pass
                    # else:
                    #     continue

            corner_rat = random.random()
            if corner_rat > 0.92:
                unit.set_task("corner_rat")
                continue

            if len(self.enemy_planets) > 0:
                # # logging.info("[2D] offensive swarm branch")
                # this takes more priority probably
                closest_docked_enemy_ship = closest_entity(ship, [s for s in self.enemy_ships if s.docking_status is hlt.entity.Ship.DockingStatus.DOCKED], max_distance=100)
                # logging.info(f"------closest_enemy_ship: {closest_docked_enemy_ship}")
                if closest_docked_enemy_ship:
                    unit.set_target(closest_docked_enemy_ship)
                    unit.set_task("hunter")
                else:
                    unit.set_target(None)
                    unit.set_task("hunter")

                continue

            if not unit.get_target(self.game_map) or not unit.get_task():
                closest_enemy_ship = closest_entity(ship, self.enemy_ships)

                if closest_enemy_ship:
                    unit.set_target(closest_enemy_ship)
                    unit.set_task("fighter")
                else:
                    unit.set_target(None)
                    unit.set_task("fighter")

    def execute_tasks(self):
        self.command_queue = []

        for unit in self.units:
            ship = ship_by_id(self.owned_ships, unit.get_ship())
            task = unit.get_task()
            logging.info(task)
            unit.age()
            # # logging.info(f"unit task: {unit.get_ship()} - age: {unit.get_age()} - {task}")
            command = None

            if task == "stay_docked" and ship.docking_status == hlt.entity.Ship.DockingStatus.DOCKED:
                unit.set_task("stay_docked")
                continue

            elif task == "avoid_danger":
                command = self.avoid_danger(unit)
                # # logging.info(f"unit command: {command}")

            elif task == "collonize_planet":
                command = self.collonize_planet(unit)

            elif task == "hunter":
                command = self.hunter(unit)

            elif task == "defender":
                command = self.hunter(unit)

            elif task == "fighter":
                command = self.hunter(unit)

            elif task == "offensive_swarm":
                command = self.offensive_swarm(unit)

            elif task == "corner_rat":
                command = self.corner_rat(unit)
            else:
                pass

            if command:
                self.command_queue.append(command)

    def avoid_danger(self, unit):
        # TODO: great improvements to be had here
        ship = ship_by_id(self.owned_ships, unit.get_ship())

        direction = 0
        # Fanning out logic
        dx = 0
        dy = 0

        for other_unit in self.units:
            if other_unit != unit:
                other_ship = ship_by_id(self.owned_ships, other_unit.get_ship())
                dx += (other_ship.x - ship.x)
                dy += (other_ship.y - ship.y)
                direction += (ship.calculate_angle_between(other_ship) + 180) % 360

        angle = (math.degrees(math.atan2(dy, dx)) + 180 ) % 360
        target_x = 10 * math.cos(math.radians(angle))
        target_y = 10 * math.sin(math.radians(angle))
        target_position = hlt.entity.Position(target_x, target_y)

        return ship.navigate(target_position,
                             self.game_map,
                             speed=int(hlt.constants.MAX_SPEED),
                             ignore_ships=False,
                             max_corrections=NAV_CORRECTIONS, angular_step=NAV_ANGLE_STEP)

    def collonize_planet(self, unit):
        ship = ship_by_id(self.owned_ships, unit.get_ship())
        planet = unit.get_target(self.game_map)  # planet_by_id(self.all_planets, unit.get_target(self.game_map))
        if not planet:
            enemy_ship = closest_entity(ship, [s for s in self.enemy_ships if
                                                              s.docking_status is hlt.entity.Ship.DockingStatus.DOCKED],
                                                       max_distance=100)
            if not enemy_ship:
                enemy_ship = closest_entity(ship, self.enemy_ships, max_distance=100)
            unit.set_task("hunter")
            unit.set_target(enemy_ship)
            return self.hunter(unit)

        if ship.can_dock(planet) and planet not in self.enemy_planets and not planet.is_full():
            # # logging.info(":::::::::::::::::: HOTSWAP TO DOCKING")
            unit.set_task("stay_docked")
            return ship.dock(planet)

        elif planet in self.enemy_planets:
            # # logging.info(":::::::::::::::::: HOTSWAP TO OFFENSIVE SWARM")
            unit.set_task("hunter")
            return self.hunter(unit)

        else:
            return ship.navigate(ship.closest_point_to(planet),
                                 self.game_map,
                                 speed=int(hlt.constants.MAX_SPEED),
                                 ignore_ships=False,
                                 max_corrections=NAV_CORRECTIONS, angular_step=NAV_ANGLE_STEP)

    def offensive_swarm(self, unit):
        ship = ship_by_id(self.owned_ships, unit.get_ship())
        planet = unit.get_target(self.game_map)  # planet_by_id(self.all_planets, unit.get_target(self.game_map))

        if not planet:
            if len(self.enemy_planets) > 0:
                unit.set_target([p for p in self.enemy_planets][0])
            else:
                return

        if ship.can_dock(planet) and planet not in self.enemy_planets and not planet.is_full():
            # # logging.info(":::::::::::::::::: HOTSWAP TO DOCKING")
            unit.set_task("stay_docked")
            return ship.dock(planet)

        target_position = swarm_point_to(ship, planet, swarmsize=3, swarmid=unit.get_ship(), offset=self.turn)
        return ship.navigate(target_position,
                             self.game_map,
                             speed=int(hlt.constants.MAX_SPEED),
                             ignore_ships=False,
                             max_corrections=NAV_CORRECTIONS, angular_step=NAV_ANGLE_STEP)

    def hunter(self, unit): # reformat to attack probably
        ship = ship_by_id(self.owned_ships, unit.get_ship())
        enemy_ship = unit.get_target(self.game_map)
        if not enemy_ship:
            return
        return ship.navigate(ship.closest_point_to(enemy_ship),
                             self.game_map,
                             speed = int(hlt.constants.MAX_SPEED),
                             ignore_ships=False,
                             max_corrections=NAV_CORRECTIONS, angular_step=NAV_ANGLE_STEP)

    def corner_rat(self, unit):
        ship = ship_by_id(self.owned_ships, unit.get_ship())
        width = self.game_map.width
        height = self.game_map.height
        target_x = None
        target_y = None
        # go to closest edge
        if ship.x < (width - ship.x):
            target_x = 0 + ship.radius
        else:
            target_x = width - ship.radius

        if ship.y < (height - ship.y):
            target_y = 0 + ship.radius
        else:
            target_y = height - ship.radius

        if target_x and target_y:
            position = hlt.entity.Position(target_x, target_y)

        return ship.navigate(ship.closest_point_to(position),
                             self.game_map,
                             speed = int(hlt.constants.MAX_SPEED),
                             ignore_ships=False,
                             max_corrections=NAV_CORRECTIONS, angular_step=NAV_ANGLE_STEP)




class Unit(object):
    def __init__(self, ship_id):
        self.ship = ship_id
        self.task = None
        self.target = None
        self.target_type = None
        self.squadron = None
        self.closest_entities = dict()
        self.closest_entity = None
        self._age = 0

    def age(self):
        self._age += 1

    def get_age(self):
        return self._age

    def set_task(self, task):
        self.task = task

    def get_task(self):
        return self.task

    def get_ship(self):
        return self.ship

    def determine_closest_entities(self, game_map):
        self.closest_entities = {"planets": sort_entities_by_distance(self.ship, game_map.all_planets()),
                                 "ships": sort_entities_by_distance(self.ship, game_map._all_ships())}

        closest_planet = dict.itervalues().next()
        closest_ship = None

    def set_target(self, target):
        if not target:
            self.target=None
        else:
            self.target_type = type(target)
            # # logging.info(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!target type is: {self.target_type}")
            self.target = target.id

    def get_target(self, game_map):
        if self.target_type == hlt.entity.Planet:
            target_entity = [p for p in game_map.all_planets() if p.id == self.target]
        elif self.target_type == hlt.entity.Ship:
            target_entity = [s for s in game_map._all_ships() if s.id == self.target]
        else:
            target_entity = None

        if target_entity:
            return target_entity[0]
        else:
            return None

    def update_reference(self, ships):
        for s in ships:
            if s.id == self.ship:
                self.ship = s.id
                break


def swarm_point_to(ship, target, min_distance=3, swarmsize=1, swarmid=1, swarmspeed=20, offset=0):
    angle = (360 / swarmsize) * swarmid + (offset * swarmspeed) % 360
    radius = target.radius + min_distance
    x = target.x + radius * math.cos(math.radians(angle))
    y = target.y + radius * math.sin(math.radians(angle))

    return hlt.entity.Position(x, y)


def ship_by_id(ships, id):
    for ship in ships:
        # # logging.info(f"searching... {ship.id} - {id}")
        if ship.id == id:
            return ship
    return None


def planet_by_id(planets, id):
    for planet in planets:
        if planet.id == id:
            return planet
    return None


def sort_entities_by_distance(ship, entities):
    unsorted_distances = {}

    for e in entities:
        unsorted_distances[e] = ship.calculate_distance_between(e)

    # # logging.info(f"unsorted: {unsorted_distances}")

    sorted_distances = OrderedDict(sorted(unsorted_distances.items(), key=lambda t: t[1]))
    # sorted_distances = OrderedDict(sorted(unsorted_distances.values()), key="honey")
    # sorted_distances = sorted(unsorted_distances.values())
    # # logging.info(f"sorted: {sorted_distances}")
    return sorted_distances


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
        return closest_entity(ship, entities, exclusions=exclusions, max_distance=max_distance * 2, depth=depth + 1)


game = hlt.Game("CommandCenterV03")
# logging.info("Initializing commmand center.")
cc = CommandCenter(game)

while True:
    cc.next_move()
    # logging.info(cc.turn)
    command_queue = cc.command_queue
    # # logging.info(f"command queue: {command_queue}")
    game.send_command_queue(command_queue)
    # # logging.info("sent...")











# # GAME START
# game = hlt.Game("Main3")
# # logging.info("Starting my Settler bot!")
# TURN = 0
#
# while True:
#     TURN += 1
#     # TURN START
#     # Update the map for the new turn and get the latest version
#     game_map = game.update_map()
#     me = game_map.get_me()
#     command_queue = []  # Here we define the set of commands to be sent to the Halite engine at the end of the turn
#
#     # Info about the fleet
#     owned_ships = me.all_ships()
#     # docked_ships = [s for s in owned_ships if s.docking_status == s.DockingStatus.DOCKED]
#     free_ships = [s for s in owned_ships if s.docking_status == s.DockingStatus.UNDOCKED]
#     enemy_ships = [s for s in game_map._all_ships() if s not in owned_ships]
#
#     # # logging.info(f"enemy ships: {enemy_ships}")
#
#     # Info about the planets
#     owned_planets = [p for p in game_map.all_planets() if p.is_owned() and p.owner == me]
#     enemy_planets = [p for p in game_map.all_planets() if p.is_owned() and p.owner != me]
#     empty_planets = [p for p in game_map.all_planets() if p.is_owned() == False]
#     full_planets = [p for p in game_map.all_planets() if p.is_full()]
#
#     ### START OF GAME LOGIC ###
#     if TURN < 2:
#         direction = 0
#
#         # Fanning out logic
#         for ship in free_ships:
#             for other_ship in free_ships:
#                 if ship.id != other_ship.id:
#                     direction += (ship.calculate_angle_between(other_ship) + 180) % 360
#
#             direction = direction / 2.0
#             docking = False
#             for planet in empty_planets:
#                 if ship.can_dock(planet):
#                     # We add the command by appending it to the command_queue
#                     command_queue.append(ship.dock(planet))
#                     docking = True
#                     break
#             if not docking:
#                 navigate_command = ship.thrust(hlt.constants.MAX_SPEED, direction)
#                 command_queue.append(navigate_command)
#
#         game.send_command_queue(command_queue)
#         continue
#
#
#     ### EARLY GAME LOGIC ###
#     if TURN < 25:
#         direction = 0
#
#         # Fanning out logic
#         for i, ship in enumerate(free_ships):
#             i *= 2
#             while (i > len(empty_planets)):
#                 i -= 1
#
#             if ship.can_dock(empty_planets[i]):
#                 command_queue.append(ship.dock(empty_planets[i]))
#             else:
#                 navigate_command = ship.navigate(ship.closest_point_to(empty_planets[i]),
#                                                  game_map,
#                                                  speed=int(hlt.constants.MAX_SPEED))
#                 command_queue.append(navigate_command)
#             # direction = 360 / len(free_ships) * float(i)
#             #
#             # # direction = direction / 2.0
#             # docking = False
#             # for planet in empty_planets:
#             #     if ship.can_dock(planet):
#             #         # We add the command by appending it to the command_queue
#             #         command_queue.append(ship.dock(planet))
#             #         docking = True
#             #         break
#             # if not docking:
#             #     navigate_command = ship.thrust(hlt.constants.MAX_SPEED, direction)
#             #     command_queue.append(navigate_command)
#
#         game.send_command_queue(command_queue)
#         continue
#
#     ### MAIN GAME LOGIC ###
#     # For every ship that I control
#     for ship in free_ships:
#         # Basic stuff, probably dict.
#         navigate_command = None
#         target_type = "planet"  # probably move to dictionary and build it to contain current tasks etc..
#
#         ## Decision logic (which target) ##
#         # Closest non-full planet I currently own
#         closest_target = closest_entity(ship, owned_planets, exclusions=full_planets)  # max distance preferable
#
#         if not closest_target:  # Closest non-empty planet that my ship could start to populate
#             closest_target = closest_entity(ship, empty_planets)
#
#         if not closest_target:  # Closest enemy my ship could attack
#             closest_target = closest_entity(ship, enemy_ships)
#             # # logging.info(f"closest_enemy: {closest_target}")
#             target_type = "enemy_ship"
#
#         if not closest_target:  # No closest target found...
#             # # logging.info(f"no closest target found. - {type(closest_target)}")
#             target_type = None
#
#         # Act upon the target if it's there
#         if target_type:
#             if target_type == "planet":
#                 if ship.can_dock(closest_target):
#                     # We add the command by appending it to the command_queue
#                     command_queue.append(ship.dock(closest_target))
#                     continue
#
#                 navigate_command = ship.navigate(
#                     ship.closest_point_to(closest_target),
#                     game_map,
#                     speed=int(hlt.constants.MAX_SPEED),
#                     ignore_ships=False)
#
#             elif target_type == "enemy_ship":
#                 # # logging.info(f"targeting ship @ {closest_target}")
#                 navigate_command = ship.navigate(
#                     closest_target,  # not the closest point to
#                     game_map,
#                     speed=int(hlt.constants.MAX_SPEED),
#                     ignore_ships=True)
#                 # # logging.info(f"{navigate_command}")
#
#         if navigate_command:
#             # # logging.info(f"adding to queue: {navigate_command}")
#             command_queue.append(navigate_command)
#         else:
#             closest_target = closest_entity(ship, enemy_ships, max_distance=50)
#             navigate_command = ship.navigate(
#                 ship.closest_point_to(closest_target),
#                 game_map,
#                 speed=int(hlt.constants.MAX_SPEED),
#                 ignore_ships=False)
#             # # logging.info("no closest planet")
#             pass
#
#     # Send our set of commands to the Halite engine for this turn
#     game.send_command_queue(command_queue)
#     # TURN END
# # GAME END
