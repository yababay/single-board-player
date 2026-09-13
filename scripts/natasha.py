from yargy2 import Parser, rule, and_, not_
from yargy2.interpretation import fact
from yargy2.predicates import gram
from yargy2.relations import gnc_relation
from yargy2.pipelines import morph_pipeline

def yargy_example(line="управляющий директор Иван Ульянов"):
    # Пример использования Yargy для распознавания имен и должностей
    Name = fact(
        'Name',
        ['first', 'last'],
    )
    Person = fact(
        'Person',
        ['position', 'name']
    )

    LAST = and_(
        gram('Surn'),
        not_(gram('Abbr')),
    )
    FIRST = and_(
        gram('Name'),
        not_(gram('Abbr')),
    )

    POSITION = morph_pipeline([
        'управляющий директор',
        'вице-мэр'
    ])

    gnc = gnc_relation()
    NAME = rule(
        FIRST.interpretation(
            Name.first
        ).match(gnc),
        LAST.interpretation(
            Name.last
        ).match(gnc)
    ).interpretation(
        Name
    )

    PERSON = rule(
        POSITION.interpretation(
            Person.position
        ).match(gnc),
        NAME.interpretation(
            Person.name
        )
    ).interpretation(
        Person
    )

    parser = Parser(PERSON)

    match = parser.match(line)
    print(match)

    #Person(
    #    position='управляющий директор',
    #    name=Name(
    #        first='Иван',
    #        last='Ульянов'
    #    )
    #)
