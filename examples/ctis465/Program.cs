public sealed record CreateCatalogItemRequest(string Name);
public sealed record CatalogItemResponse(Guid Id, string Name);

public sealed class CatalogItemHandler
{
    public Task<CatalogItemResponse> HandleAsync(
        CreateCatalogItemRequest request,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        string name = request.Name.Trim();
        if (name.Length is < 2 or > 80)
        {
            throw new ArgumentException("Name must contain 2 to 80 characters.", nameof(request));
        }
        return Task.FromResult(new CatalogItemResponse(Guid.Parse("11111111-1111-1111-1111-111111111111"), name));
    }
}

internal static class Program
{
    private static async Task Main()
    {
        var handler = new CatalogItemHandler();
        CatalogItemResponse response = await handler.HandleAsync(
            new CreateCatalogItemRequest("  Atlas  "), CancellationToken.None);
        if (response.Name != "Atlas") throw new InvalidOperationException("normalization failed");

        try
        {
            await handler.HandleAsync(new CreateCatalogItemRequest("x"), CancellationToken.None);
            throw new InvalidOperationException("validation was not enforced");
        }
        catch (ArgumentException)
        {
            Console.WriteLine("DOTNET_SLICE_OK");
        }
    }
}
