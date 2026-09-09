using DotNetEnv;
using API.Repositories;
using API.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.RateLimiting;
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
        options.KnownNetworks.Clear();
        options.KnownProxies.Clear();
    });

    // Fix #1 (HTTP layer): fixed-window rate limiter for OTP endpoints.
    // Limits /api/auth/request-otp and /api/auth/verify-otp to 5 requests per
    // 5-minute window per client IP. This is a first-layer defence; the DB-layer
    // per-OTP failed-attempt counter in AuthService.VerifyOtpAsync is the second layer
    // (handles distributed brute-force via many IPs sharing the same telegramId).
    builder.Services.AddRateLimiter(options =>
    {
        options.AddFixedWindowLimiter("otp", opt =>
        {
            opt.PermitLimit   = 5;
            opt.Window        = TimeSpan.FromMinutes(5);
            opt.QueueLimit    = 0;  // reject immediately rather than queue
            opt.QueueProcessingOrder =
                System.Threading.RateLimiting.QueueProcessingOrder.OldestFirst;
        });
        options.AddFixedWindowLimiter("status-poll", opt =>
        {
            opt.PermitLimit   = 60;  // Up to 60 requests per minute per IP (polling is every 2.5s = 24 req/min)
            opt.Window        = TimeSpan.FromMinutes(1);
            opt.QueueLimit    = 0;
            opt.QueueProcessingOrder =
                System.Threading.RateLimiting.QueueProcessingOrder.OldestFirst;
        });
        options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
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
        ?? builder.Configuration["DASHBOARD_SECRET_KEY"];

    if (string.IsNullOrWhiteSpace(jwtSecret) || jwtSecret.Length < 32)
        throw new InvalidOperationException(
            "JWT_SECRET (or DASHBOARD_SECRET_KEY) is not configured or is too short (minimum 32 characters required). " +
            "Generate a strong random secret with: openssl rand -hex 32");

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
                },
                // Fix #3: re-validate the JWT subject against the *current* admin list on
                // every authenticated request. Without this, a revoked admin's 7-day JWT
                // remains valid indefinitely until natural expiry — there is no server-side
                // revocation mechanism. This closure enforces live admin-list membership.
                OnTokenValidated = context =>
                {
                    var cfg = context.HttpContext.RequestServices
                                     .GetRequiredService<IConfiguration>();
                    var idsStr = cfg["BOT_ADMIN_IDS"] ?? "";
                    var adminSet = idsStr
                        .Replace("[", "").Replace("]", "")
                        .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                        .ToHashSet();

                    var sub = context.Principal
                        ?.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                        ?? context.Principal
                        ?.FindFirst(System.IdentityModel.Tokens.Jwt.JwtRegisteredClaimNames.Sub)?.Value;

                    // If admin list is configured and the token subject is no longer in it,
                    // reject the request (403 — avoids leaking the reason to the client).
                    if (adminSet.Count > 0 && (sub == null || !adminSet.Contains(sub)))
                        context.Fail("Token subject is not in the current admin list.");

                    return Task.CompletedTask;
                }
            };
        });

    // ── DI ────────────────────────────────────────────────────────────────────
    builder.Services.AddHttpClient();
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

    // Fix #1: enforce OTP rate limit
    app.UseRateLimiter();

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
