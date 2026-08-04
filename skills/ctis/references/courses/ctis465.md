# CTIS465 — .NET microservices with MediatR and EF Core

You are extending a template-generated microservice solution. Every domain is built the same way, and the value of the work is that the shape repeats exactly. A feature written in a different style is worse than one written in the template's style, even when it is shorter.

Evidence note: this module is derived from one student's collected material for a single section in a single term. The conventions it states recur across that material and are reliable. What varies by section, instructor or term is not established by it: grading weights, submission mechanics, and which topics an exam covers should be asked for rather than assumed.

## Teaching posture

Teach by repetition of one vertical slice. The same request-handler-response triple is written for Games, Genres, Publishers, Users, Roles, and Groups, so the student learns the shape by producing it, not by reading about it. Name the layer that each piece of code belongs to before writing it. Comment every step in plain English, including the obvious ones; the comments are part of the deliverable.

When a student asks where code belongs, answer with the layer first: protocol concerns go in the controller, business rules go in the handler, data shape goes in the domain.

## Scope

Layered service solutions, CQRS-style request handling with MediatR, EF Core with SQLite, DTO request and response models, validation with data annotations, controller error handling and HTTP status codes, Swagger, and repeating a vertical slice across domains.

Not covered by the course material available here: Docker, Kubernetes, an API gateway, gRPC, and message brokers such as RabbitMQ or Kafka. Do not present those as the way this course does microservices.

## The solution shape

Two services plus one shared library, each service split into an API project and an APP project.

```text
CORE/
  APP/
    Models/     Request, Response, CommandResponse
    Services/   Service<TEntity>
Games.API/      controllers, Program.cs, appsettings.json
Games.APP/
  Domain/       Game, Publisher, Genre, GamesDb (DbContext)
  Features/
    Games/      GameCreateHandler.cs, GameQueryHandler.cs, ...
    Genres/
    Publishers/
Users.API/
Users.APP/
```

Each responsibility has exactly one home:

| Layer | Holds | Never holds |
|---|---|---|
| `X.API` controller | routing, HTTP status codes, logging, try/catch | business rules, EF queries |
| `X.APP` handler | validation, duplicate checks, entity mapping, persistence | HTTP types, `IActionResult` |
| `X.APP` domain | entities and the `DbContext` | request or response DTOs |
| `CORE.APP` | base `Request`, `Response`, `CommandResponse`, `Service<T>` | anything domain specific |

`CORE.APP.Services.Service<TEntity>` is the base every handler inherits. Its protected members, with their exact names:

```csharp
protected virtual IQueryable<TEntity> DbSet()
protected async Task CreateAsync(TEntity entity, CancellationToken cancellationToken, bool save = true)
protected async Task UpdateAsync(TEntity entity, CancellationToken cancellationToken, bool save = true)
protected async Task DeleteAsync(TEntity entity, CancellationToken cancellationToken, bool save = true)
protected virtual async Task<int> SaveAsync(CancellationToken cancellationToken)
protected void Delete<TRelationalEntity>(List<TRelationalEntity> relationalEntities)
```

`ServiceBase` adds the two response helpers and the culture used for formatting:

```csharp
protected CommandResponse Success(string message, int id)
protected CommandResponse Error(string message)
protected CultureInfo CultureInfo
```

The `Async` suffix is part of the name. `Create(...)` does not exist and will not compile. Pass `save: false` when several writes belong to one transaction, then call `SaveAsync` once.

One feature folder holds all the operations for one entity, and one file holds the request, the response, and the handler for one operation.

## Skeletons

### Command: request, handler, response

```csharp
using CORE.APP.Models;
using CORE.APP.Services;
using Games.APP.Domain;
using MediatR;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;

namespace Games.APP.Features.Games
{
    public class GameCreateRequest : Request, IRequest<CommandResponse>
    {
        [Required, StringLength(200)]
        public string Title { get; set; }

        public DateTime? ReleaseDate { get; set; }

        public double Price { get; set; }

        public bool IsTopSeller { get; set; }

        public int? PublisherId { get; set; }

        public List<int> GenreIds { get; set; } = new List<int>();
    }

    public class GameCreateHandler : Service<Game>, IRequestHandler<GameCreateRequest, CommandResponse>
    {
        public GameCreateHandler(DbContext db) : base(db)
        {
        }

        public async Task<CommandResponse> Handle(GameCreateRequest request, CancellationToken cancellationToken)
        {
            // Reject a duplicate before touching the database
            if (await DbSet().AnyAsync(g => g.Title == request.Title.Trim(), cancellationToken))
                return Error($"Game with the same title: \"{request.Title.Trim()}\" exists!");

            // Map the request to the entity
            var entity = new Game
            {
                GenreIds = request.GenreIds,
                IsTopSeller = request.IsTopSeller,
                Price = request.Price,
                PublisherId = request.PublisherId,
                ReleaseDate = request.ReleaseDate,
                Title = request.Title?.Trim()
            };

            // Persist and return the shared command response
            await CreateAsync(entity, cancellationToken);

            return Success("Game created successfully.", entity.Id);
        }
    }
}
```

Four fixed moves in every command handler: uniqueness check first, then mapping, then persistence, then a `CommandResponse`. Trim every incoming string with `?.Trim()`, in both the check and the mapping, or a trailing space defeats the duplicate test.

### Query: raw values plus formatted values

```csharp
    public class GameQueryRequest : Request, IRequest<IQueryable<GameQueryResponse>>
    {
    }

    public class GameQueryResponse : Response
    {
        // entity properties
        public string Title { get; set; }
        public DateTime? ReleaseDate { get; set; }
        public double Price { get; set; }
        public bool IsTopSeller { get; set; }
        public int? PublisherId { get; set; }
        public List<int> GenreIds { get; set; }

        // custom properties
        public string IsTopSellerF { get; set; }
        public string PriceF { get; set; }
        public string ReleaseDateF { get; set; }
        public string PublisherF { get; set; }
        public string GenresF { get; set; }

        public PublisherQueryResponse Publisher { get; set; }
        public List<GenreQueryResponse> Genres { get; set; }
    }

    public class GameQueryHandler : Service<Game>, IRequestHandler<GameQueryRequest, IQueryable<GameQueryResponse>>
    {
        public GameQueryHandler(DbContext db) : base(db)
        {
        }

        protected override IQueryable<Game> DbSet()
        {
            return base.DbSet()
                .Include(g => g.Publisher)
                .Include(g => g.GameGenres).ThenInclude(gg => gg.Genre);
        }

        public Task<IQueryable<GameQueryResponse>> Handle(GameQueryRequest request, CancellationToken cancellationToken)
        {
            var query = DbSet().OrderBy(g => g.Title).Select(g => new GameQueryResponse
            {
                Id = g.Id,
                Title = g.Title,
                ReleaseDate = g.ReleaseDate,
                Price = g.Price,
                IsTopSeller = g.IsTopSeller,

                IsTopSellerF = g.IsTopSeller ? "Yes" : "No",
                PriceF = g.Price.ToString("C2"),
                ReleaseDateF = g.ReleaseDate.HasValue ? g.ReleaseDate.Value.ToString("dd/MM/yyyy") : string.Empty,
                PublisherF = g.Publisher.Name,
                GenresF = string.Join(", ", g.GameGenres.Select(gg => gg.Genre.Name))
            });

            return Task.FromResult(query);
        }
    }
```

The `F` suffix marks a display string derived from the raw value next to it. Send both: the raw property for clients that compute, the `F` property for clients that render. Never replace the raw value with its formatted form.

Override `DbSet()` in the query handler to attach the `Include` chain once, so every query in that feature loads the same graph.

### Controller

```csharp
#nullable disable
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using MediatR;
using CORE.APP.Models;
using Games.APP.Features.Games;

namespace Games.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class GamesController : ControllerBase
    {
        private readonly ILogger<GamesController> _logger;
        private readonly IMediator _mediator;

        // Constructor: injects the logger and the mediator
        public GamesController(ILogger<GamesController> logger, IMediator mediator)
        {
            _logger = logger;
            _mediator = mediator;
        }

        // GET: api/Games
        [HttpGet]
        public async Task<IActionResult> Get()
        {
            try
            {
                // Send a query request to get the query response
                var response = await _mediator.Send(new GameQueryRequest());
                // Convert the query response to a list
                var list = await response.ToListAsync();
                // If there are items, return them with 200 OK
                if (list.Any())
                    return Ok(list);
                // If no items found, return 204 No Content
                return NoContent();
            }
            catch (Exception exception)
            {
                // Log the exception
                _logger.LogError("GamesGet Exception: " + exception.Message);
                // Return 500 with a safe message
                return StatusCode(StatusCodes.Status500InternalServerError, "An exception occurred during getting games.");
            }
        }

        // POST: api/Games
        [HttpPost]
        public async Task<IActionResult> Post(GameCreateRequest request)
        {
            try
            {
                if (ModelState.IsValid)
                {
                    var response = await _mediator.Send(request);
                    if (response.IsSuccessful)
                        return Ok(response);
                    ModelState.AddModelError("GamesPost", response.Message);
                }
                // Flatten the model state into the shared response shape
                return BadRequest(new CommandResponse(false,
                    string.Join("|", ModelState.Values.SelectMany(v => v.Errors).Select(e => e.ErrorMessage))));
            }
            catch (Exception exception)
            {
                _logger.LogError("GamesPost Exception: " + exception.Message);
                return StatusCode(StatusCodes.Status500InternalServerError, "An exception occurred during posting the game.");
            }
        }
    }
}
```

The status codes are fixed: `200 Ok` with data, `204 NoContent` for an empty list, `400 BadRequest` with the `ModelState` for a rejected request, `500` with a generic message for an unexpected exception. The exception detail goes to the log, never to the response.

Every action is wrapped in try/catch. The log message names the action, as in `GamesPost Exception: `.

### Program.cs

```csharp
var builder = WebApplication.CreateBuilder(args);

// Register the database context for this service
var connectionString = builder.Configuration.GetConnectionString(nameof(GamesDb));
builder.Services.AddDbContext<DbContext, GamesDb>(options => options.UseSqlite(connectionString));

// Register MediatR handlers found in the loaded assemblies
foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
{
    builder.Services.AddMediatR(config => config.RegisterServicesFromAssemblies(assembly));
}

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

app.Run();
```

`AddDbContext<DbContext, GamesDb>` registers the concrete context under the base type, which is what lets `Service<TEntity>` take a plain `DbContext` in its constructor. Each service owns its own database and its own connection string.

### Adding a new domain

Repeat the slice in this order, changing only the entity name:

1. Entity in `X.APP/Domain`, plus a `DbSet<T>` on the context.
2. Migration and database update.
3. `Features/<Entity>/<Entity>CreateHandler.cs` with its request, handler, and `CommandResponse`.
4. `<Entity>QueryHandler.cs` with the response carrying raw and `F` properties.
5. Update and delete handlers, same shape.
6. Controller with `Get`, `Post`, `Put`, `Delete`, each wrapped in try/catch.
7. Check it in Swagger.

## Rules with rewrites

**Business rule in the controller.**
A duplicate-title check inside the action becomes an `AnyAsync` check at the top of the handler, with the controller only sending the request.

**EF query in the controller.**
`_db.Games.ToListAsync()` in an action becomes `_mediator.Send(new GameQueryRequest())`.

**HTTP type in the handler.**
A handler returning `IActionResult` becomes one returning `CommandResponse` or `IQueryable<TResponse>`, with the controller mapping that to a status code.

**Entity returned to the client.**
`return Ok(game);` becomes `return Ok(gameQueryResponse);`, so persistence fields and navigation properties do not leak.

**Untrimmed input.**
`Title = request.Title` becomes `Title = request.Title?.Trim()`, and the duplicate check trims as well.

**Formatting on the raw property.**
`Price = g.Price.ToString("C2")` becomes `Price = g.Price` plus `PriceF = g.Price.ToString("C2")`.

**Validation only in the handler.**
A missing `[Required]` becomes a data annotation on the request property, with the controller checking `ModelState.IsValid`.

**Exception text returned to the caller.**
`return StatusCode(500, exception.Message);` becomes a logged exception plus a generic message in the response.

**Swallowed failure.**
A handler returning `Success(...)` after a failed check becomes one returning `Error(...)` with a message the controller can put into `ModelState`.

**Missing includes.**
A query whose navigation properties are null becomes one whose `DbSet()` override adds the `Include` chain.

**Synchronous data access.**
`DbSet().ToList()` becomes `await DbSet().ToListAsync(cancellationToken)`, and the `CancellationToken` is passed through.

**Persistence helper called without its suffix.**
`await Create(entity, cancellationToken)` becomes `await CreateAsync(entity, cancellationToken)`. The same applies to `UpdateAsync`, `DeleteAsync` and `SaveAsync`; the short names do not exist on `Service<TEntity>`.

**Raw model state returned.**
`return BadRequest(ModelState);` becomes `return BadRequest(new CommandResponse(false, string.Join("|", ModelState.Values.SelectMany(v => v.Errors).Select(e => e.ErrorMessage))));`, so a rejected command answers in the same shape as a successful one.

## Failure modes

- Registering the context as `AddDbContext<GamesDb>` only, so `Service<TEntity>` cannot resolve a plain `DbContext`.
- Forgetting to add the migration after changing an entity, so the query fails at runtime with a missing column.
- A `Select` projection that calls a method EF cannot translate, which throws only when the query is enumerated.
- Returning `IQueryable` from the controller without materialising it, so the connection is already disposed when it is read.
- Comparing a nullable foreign key against a value without checking `HasValue`.
- A many-to-many relation loaded without `ThenInclude`, so the join entity is present but the target is null.
- Two services sharing one database file, which breaks the one-database-per-service rule the solution is built on.
- A response class that inherits the wrong base, so `Id` is missing from the payload.

## Verification

Before reporting the work as done, confirm all of these:

- The request, response, and handler for one operation live in one file, inside the entity's feature folder.
- The handler contains no HTTP type, and the controller contains no EF query.
- Every command handler checks for a duplicate, trims strings, maps explicitly, and returns a `CommandResponse`.
- Every query response carries the raw property and its `F` counterpart where a display form is needed.
- Every controller action is wrapped in try/catch, logs with the action name, and returns 200, 204, 400, or 500 as appropriate.
- Data annotations are present on the request, and `ModelState.IsValid` is checked.
- The new entity has a `DbSet<T>` and a migration.
- Swagger lists the new endpoints and they respond.

## Workflow

1. Name the entity and the operation, and say which layer each piece will live in.
2. Write or extend the domain entity and the `DbSet<T>`, then add the migration.
3. Write the request with its data annotations.
4. Write the handler: duplicate check, mapping, persistence, response.
5. For queries, write the response with raw and `F` properties and override `DbSet()` for the includes.
6. Write the controller action with try/catch, logging, and the fixed status codes.
7. Comment each step in plain English as the template does.
8. Check it in Swagger and report which endpoints you exercised and which you could not.
