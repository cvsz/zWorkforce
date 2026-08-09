using Microsoft.UI.Xaml;
using ZWorkforceClient.Services;

namespace ZWorkforceClient;

public partial class App : Application
{
    public App()
    {
        InitializeComponent();
        Session = new ClientSession();
    }

    public static App Current => (App)Application.Current;

    public ClientSession Session { get; }

    public MainWindow? MainWindow { get; private set; }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        MainWindow = new MainWindow();
        MainWindow.Activate();
    }
}
