namespace API.Models.Requests;

public class OtpRequestDto
{
    public long TelegramId { get; set; }
}

public class OtpVerifyDto
{
    public long TelegramId { get; set; }
    public string Otp { get; set; } = string.Empty;
}
