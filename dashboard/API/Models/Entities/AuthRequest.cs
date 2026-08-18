using Microsoft.AspNetCore.Mvc;

namespace API.Models.Entities
{
    public class AuthRequest : Controller
    {
        public IActionResult Index()
        {
            return View();
        }
    }
}
