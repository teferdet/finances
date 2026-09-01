using DotNetEnv;
using API.Repositories;
using API.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.IdentityModel.Tokens;
using System.Text;
using Serilog;


if (File.Exists(".env"))
    Env.Load(".env");
else if (File.Exists("../../.env"))
    Env.Load("../../.env");
else if (File.Exists("../.env"))
    Env.Load("../.env");

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .WriteTo.File("/app/logs/api.log", rollingInterval: RollingInterval.Day)
    .CreateLogger();

try
{
    var builder = WebApplication.CreateBuilder(args);
    builder.Host.UseSerilog();

    // ── ForwardedHeaders (nginx → X-Forwarded-For / X-Forwarded-Proto) ────────
    builder.Services.Configure<ForwardedHeadersOptions>(options =>
    {
        options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
        // Trust the nginx container / loopback proxy only
        options.KnownNetworks.Clear();
        options.KnownProxies.Clear();
    });

    // ── CORS ──────────────────────────────────────────────────────────────────
    // Allow specific origins from env (comma-separated), or allow same-origin only.
    var corsOrigins = (builder.Configuration["DASHBOARD_CORS_ORIGINS"] ?? "")
        .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

    if (corsOrigins.Length > 0)
    {
        builder.Services.AddCors(opts =>
            opts.AddDefaultPolicy(policy =>
                policy.WithOrigins(corsOrigins)
                      .AllowAnyHeader()
                      .AllowAnyMethod()
                      .AllowCredentials()));
    }

    // ── JWT Auth ──────────────────────────────────────────────────────────────
    var jwtSecret = builder.Configuration["JWT_SECRET"]
        ?? builder.Configuration["DASHBOARD_SECRET_KEY"]
        ?? (builder.Environment.IsDevelopment() ? "ThisIsADefaultSecretKeyForDevelopmentOnly123!" : null);

    if (string.IsNullOrWhiteSpace(jwtSecret) || jwtSecret.Length < 32)
        throw new InvalidOperationException(
            "JWT_SECRET (or DASHBOARD_SECRET_KEY) is not configured or is too short (minimum 32 characters required).");

    builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
        .AddJwtBearer(options =>
        {
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidateIssuer           = true,
                ValidateAudience         = true,
                ValidateLifetime         = true,
                ValidateIssuerSigningKey = true,
                ValidIssuer              = "FinancesDashboard",
                ValidAudience            = "FinancesDashboard",
                IssuerSigningKey         = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecret))
            };

            // Read JWT from httpOnly cookie (set by /api/auth/verify-otp)
            options.Events = new JwtBearerEvents
            {
                OnMessageReceived = context =>
                {
                    if (context.Request.Cookies.ContainsKey("dash_session"))
                        context.Token = context.Request.Cookies["dash_session"];
                    return Task.CompletedTask;
                }
            };
        });

    // ── DI ────────────────────────────────────────────────────────────────────
    builder.Services.AddSingleton<MongoContext>();
    builder.Services.AddScoped<AuthService>();
    builder.Services.AddScoped<StatsService>();
    builder.Services.AddScoped<ConfigService>();
    builder.Services.AddScoped<UserDataService>();

    builder.Services.AddControllers()
        .AddJsonOptions(options =>
        {
            options.JsonSerializerOptions.PropertyNamingPolicy =
                System.Text.Json.JsonNamingPolicy.SnakeCaseLower;
        });
    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddSwaggerGen();

    // ── Build ─────────────────────────────────────────────────────────────────
    var app = builder.Build();

    // Must be first: trust X-Forwarded-* headers from nginx
    app.UseForwardedHeaders();

    if (app.Environment.IsDevelopment())
    {
        app.UseSwagger();
        app.UseSwaggerUI();
    }

    // Conditional CORS (only when origins are configured)
    if (corsOrigins.Length > 0)
        app.UseCors();

    // app.UseHttpsRedirection(); // Removed for Docker / NGINX reverse proxy compatibility

    app.UseAuthentication();
    app.UseAuthorization();

    app.MapControllers();

    // Ensure MongoDB indexes exist (idempotent — safe on every restart)
    await using (var scope = app.Services.CreateAsyncScope())
    {
        var mongo = scope.ServiceProvider.GetRequiredService<MongoContext>();
        try
        {
            await mongo.EnsureIndexesAsync();
            Log.Information("MongoDB indexes ensured.");
        }
        catch (Exception ex)
        {
            Log.Warning(ex, "Failed to ensure MongoDB indexes (non-fatal).");
        }
    }

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
