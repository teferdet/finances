using Microsoft.AspNetCore.Mvc;

namespace API.Models.Entities
{
    public class User : Controller
    {
        public IActionResult Index()
        {
            return View();
        }
    }
}
