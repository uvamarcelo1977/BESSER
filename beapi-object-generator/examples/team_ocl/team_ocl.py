"""Modelo B-UML de ejemplo para beapi_gen.py --conformance: dos clases, una asociacion y dos invariantes OCL.

    Team (name: str, maxPlayers: int)  --players 0..*-->  Player (name: str, age: int)

team_ocl.json (el proyecto del editor web que usa beapi_gen.py) se obtiene de este archivo con:
    PYTHONPATH=.. ../venv/bin/python examples/team_ocl/team_ocl.py
(desde beapi-object-generator/), o importando este .py en el editor web de BESSER.
"""
from besser.BUML.metamodel.structural import (
    BinaryAssociation, Class, Constraint, DomainModel, IntegerType, Multiplicity, Property, StringType,
    UNLIMITED_MAX_MULTIPLICITY,
)

Team = Class(name="Team")
Team.attributes = {Property(name="name", type=StringType), Property(name="maxPlayers", type=IntegerType)}

Player = Class(name="Player")
Player.attributes = {Property(name="name", type=StringType), Property(name="age", type=IntegerType)}

# unidireccional: el equipo conoce a sus jugadores (Team.players); el jugador no conoce a su equipo
team_players = BinaryAssociation(name="team_players", ends={
    Property(name="team", type=Team, multiplicity=Multiplicity(1, 1), is_navigable=False),
    Property(name="players", type=Player, multiplicity=Multiplicity(0, UNLIMITED_MAX_MULTIPLICITY)),
})

# invariantes OCL
AdultPlayer = Constraint(name="AdultPlayer", context=Player, language="OCL",
                         expression="context Player inv AdultPlayer: self.age >= 18")
TeamNotOverCapacity = Constraint(name="TeamNotOverCapacity", context=Team, language="OCL",
                                 expression="context Team inv TeamNotOverCapacity: "
                                            "self.players->size() <= self.maxPlayers")

domain_model = DomainModel(name="TeamOCL", types={Team, Player}, associations={team_players},
                           constraints={AdultPlayer, TeamNotOverCapacity})


if __name__ == "__main__":   # escribe team_ocl.json: un proyecto del editor web con este diagrama de clases
    import json
    import os
    from besser.utilities.web_modeling_editor.backend.services.converters.buml_to_json.project_converter import (
        project_to_json)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(__file__, encoding="utf-8") as f:
        project = project_to_json(f.read())
    project["name"] = "team_ocl"
    project["diagrams"]["ClassDiagram"][0]["title"] = domain_model.name
    with open(os.path.join(here, "team_ocl.json"), "w", encoding="utf-8") as f:
        json.dump({"project": project}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("-> " + os.path.join(here, "team_ocl.json"))
