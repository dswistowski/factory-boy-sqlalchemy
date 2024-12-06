# factory-boy-sqlalchemy

## Why this package was created?

Most of factory-boy sqlalchemy packages, puts session in meta, 
so the factory is bound to session during creation.

In this package two helper functions are provided: `make_async_sqlalchemy_factory` and `make_sync_sqlalchemy_factory`, 
which takes session less factory and bind to the session - it allows to use the same factory with async and sync session

## Example

```python
import factory
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    ...

class User(Base):
    id_ = factory.Faker("name") 
    order = factory.Faker("between", from_=1, to=151)
```
