using Microsoft.AspNetCore.Identity;

namespace webowka.Data.Seed;

public static class IdentitySeeder
{
    public static async Task SeedRolesAndDoctorAsync(
        IServiceProvider serviceProvider)
    {
        var roleManager =
            serviceProvider.GetRequiredService<RoleManager<IdentityRole>>();

        var userManager =
            serviceProvider.GetRequiredService<UserManager<IdentityUser>>();

        string[] roles =
        {
            "Doctor",
            "Patient"
        };

        foreach (var role in roles)
        {
            if (!await roleManager.RoleExistsAsync(role))
            {
                await roleManager.CreateAsync(
                    new IdentityRole(role));
            }
        }

        var doctorEmail = "admin@webowka.pl";

        var doctor =
            await userManager.FindByEmailAsync(doctorEmail);

        if (doctor == null)
        {
            doctor = new IdentityUser
            {
                UserName = doctorEmail,
                Email = doctorEmail,
                EmailConfirmed = true
            };

            await userManager.CreateAsync(
                doctor,
                "Admin123!"
            );

            await userManager.AddToRoleAsync(
                doctor,
                "Doctor"
            );
        }
        var patientEmail = "pacjent1@test.pl";

        var patient =
            await userManager.FindByEmailAsync(patientEmail);

        if (patient != null &&
            !await userManager.IsInRoleAsync(patient, "Patient"))
        {
            await userManager.AddToRoleAsync(
                patient,
                "Patient");
        }
    }
}