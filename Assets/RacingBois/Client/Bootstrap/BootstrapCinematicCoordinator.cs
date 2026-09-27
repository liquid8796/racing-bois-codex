using System;
using RacingBois.Client.Adapters;
using RacingBois.Client.Application;
using RacingBois.Client.Presentation;
using UnityEngine;
using UnityEngine.UIElements;

namespace RacingBois.Client.Bootstrap
{
    /// <summary>Composes optional scenes with UI/music; the caller retains all race and economy authority.</summary>
    [DisallowMultipleComponent]
    public sealed class BootstrapCinematicCoordinator : MonoBehaviour
    {
        public event Action ContentRequired;
        public CinematicDirector Director { get; private set; }
        public CinematicGalleryView Gallery { get; private set; }
        public bool BlocksGameplayInput => Director != null && Director.IsPlaying || Gallery != null && Gallery.IsOpen;
        public bool IsOpen => Gallery != null && Gallery.IsOpen;
        private P08MusicDirector music;
        private Func<string, string> resolveMusic;
        private Func<bool> canPlay;
        private P08MusicDirector.PlaybackState priorMusic;
        private bool capturedMusic, returnToGallery, suppressRestore, introShown, initialized;

        public void Initialize(RaceStageView stage, UIDocument document, P08MusicDirector musicPlayer, Func<string, string> resolveValidatedMusicUrl, Func<bool> allowed)
        {
            if (initialized) return;
            if (stage == null || document == null || musicPlayer == null || resolveValidatedMusicUrl == null) throw new ArgumentNullException(nameof(stage));
            initialized = true; music = musicPlayer; resolveMusic = resolveValidatedMusicUrl; canPlay = allowed;
            Director = gameObject.AddComponent<CinematicDirector>(); Director.Initialize(stage);
            Gallery = gameObject.AddComponent<CinematicGalleryView>(); Gallery.Initialize(document, Director);
            Gallery.PlayRequested += PlayFromGallery; Director.Completed += PlaybackCompleted; Director.MusicRequested += PlayMusic;
        }
        public void OpenGallery()
        {
            if (!initialized || canPlay != null && !canPlay()) return;
            if (Director.IsPlaying) StopForGameplay();
            Gallery.Show();
            if (ContentRegistry.Actors == null || ContentRegistry.Route == null)
            { Gallery.ShowError("Đang chờ nội dung 3D của đường đua…"); ContentRequired?.Invoke(); }
        }
        public bool PlayIntro()
        {
            if (introShown) return false;
            bool started = Play(CinematicCatalog.ForEvent(CinematicRole.Intro, 0), false);
            if (started) introShown = true; return started;
        }
        public bool PlayShowcase(int bikeIndex)
        {
            if (bikeIndex < 0 || bikeIndex >= 15) return false;
            foreach (var sequence in CinematicCatalog.ForRole(CinematicRole.Showcase)) if (sequence.BikeIndex == bikeIndex) return Play(sequence, false);
            return false;
        }
        public bool PlayOutcome(CinematicRole role, int variant)
        {
            if (role != CinematicRole.Win && role != CinematicRole.Lose && role != CinematicRole.Wreck && role != CinematicRole.Busted && role != CinematicRole.Level && role != CinematicRole.FinalWin) return false;
            return Play(CinematicCatalog.ForEvent(role, variant), false);
        }
        public bool Play(CinematicDefinition definition, bool reopenGallery = false)
        {
            if (!initialized || canPlay != null && !canPlay()) return false;
            if (Director.IsPlaying) StopForGameplay();
            priorMusic = music.CaptureState(); capturedMusic = true; returnToGallery = reopenGallery;
            music.UnlockFromUserGesture();
            if (!Director.StartPlayback(definition))
            { capturedMusic = false; Gallery.ShowError(Director.LastError); return false; }
            Gallery.ShowPlayback(); return true;
        }
        private void PlayFromGallery(CinematicDefinition definition) { Play(definition, true); }
        private void PlayMusic(string id)
        {
            string url = resolveMusic(id);
            if (!string.IsNullOrEmpty(url)) music.Play(id, url, true, .18f);
            else music.SetDucking(.35f);
        }
        private void PlaybackCompleted(CinematicDefinition definition, bool skipped)
        {
            Gallery.HidePlayback(); music.SetDucking(1);
            if (capturedMusic && !suppressRestore) music.RestoreState(priorMusic); capturedMusic = false;
            if (returnToGallery && !suppressRestore) Gallery.Show(); returnToGallery = false;
        }
        public void StopForGameplay(bool restoreMusic = true)
        {
            if (!initialized) return;
            bool restore = capturedMusic && restoreMusic; var state = priorMusic;
            suppressRestore = true;
            try { Director.Stop(true); Gallery.HidePlayback(); Gallery.Hide(); }
            finally { suppressRestore = false; capturedMusic = false; returnToGallery = false; music.SetDucking(1); }
            if (restore) music.RestoreState(state);
        }
        public void PrepareContentUnload()
        {
            if (!initialized) return;
            bool keepGallery = Gallery.IsOpen; StopForGameplay(false);
            if (keepGallery) { Gallery.Show(); Gallery.ShowError("Đang tải nội dung 3D của đường đua…"); }
        }
        public bool HandleBack() => initialized && Gallery.HandleBack();
        public void ApplyPreferences(bool reducedMotion, bool audioEnabled, float volume = 1)
        { if (!initialized) return; Director.ReducedMotion = reducedMotion; music.SetMix(audioEnabled, volume); }
        private void OnDestroy()
        {
            if (!initialized) return;
            if (Director != null) { Director.Completed -= PlaybackCompleted; Director.MusicRequested -= PlayMusic; Director.Stop(true); }
            if (Gallery != null) Gallery.PlayRequested -= PlayFromGallery;
            ContentRequired = null;
        }
    }
}
