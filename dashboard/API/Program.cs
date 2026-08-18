using DotNetEnv;
using API.Repositories;
using API.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using System.Text;
using Serilog;


if (File.Exists(".env"))
{
    Env.Load(".env");
}
else if (File.Exists("../../.env"))
{
    Env.Load("../../.env");
}
else if (File.Exists("../.env"))
{
    Env.Load("../.env");
}

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .WriteTo.File("/app/logs/api.log", rollingInterval: RollingInterval.Day)
    .CreateLogger();

try
{
    var builder = WebApplication.CreateBuilder(args);
    builder.Host.UseSerilog();


var jwtSecret = builder.Configuration["JWT_SECRET"] 
    ?? builder.Configuration["DASHBOARD_SECRET_KEY"]
    ?? (builder.Environment.IsDevelopment() ? "ThisIsADefaultSecretKeyForDevelopmentOnly123!" : null);

if (string.IsNullOrWhiteSpace(jwtSecret) || jwtSecret.Length < 32)
{
    throw new InvalidOperationException("JWT_SECRET (or DASHBOARD_SECRET_KEY) is not configured or is too short (minimum 32 characters required).");
}

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = "FinancesDashboard",
            ValidAudience = "FinancesDashboard",
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecret))
        };
        
        
        options.Events = new JwtBearerEvents
        {
            OnMessageReceived = context =>
            {
                if (context.Request.Cookies.ContainsKey("dash_session"))
                {
                    context.Token = context.Request.Cookies["dash_session"];
                }
                return Task.CompletedTask;
            }
        };
    });


builder.Services.AddSingleton<MongoContext>();
builder.Services.AddScoped<AuthService>();
builder.Services.AddScoped<StatsService>();
builder.Services.AddScoped<ConfigService>();

builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.SnakeCaseLower;
    });
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// app.UseHttpsRedirection(); // Removed for Docker / NGINX reverse proxy compatibility


    app.UseAuthentication();
    app.UseAuthorization();

    app.MapControllers();

    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
}
