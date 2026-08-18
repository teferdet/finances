namespace API.Models.Requests;

public class ConfigUpdateDto
{
    public string Section { get; set; } = string.Empty;
    public Dictionary<string, object> Settings { get; set; } = new();
}

public class FeaturePatchDto
{
    public string Feature { get; set; } = string.Empty;
    public bool Value { get; set; }
}
