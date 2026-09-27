using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Threading;
using RacingBois.Client.Adapters;
sealed class FrameContext:SynchronizationContext
{
    readonly ConcurrentQueue<Tuple<SendOrPostCallback,object>> queue=new ConcurrentQueue<Tuple<SendOrPostCallback,object>>();
    public int Posts,MaximumQueued;
    public override void Post(SendOrPostCallback callback,object state){Interlocked.Increment(ref Posts);queue.Enqueue(Tuple.Create(callback,state));}
    public void Frame(){int count=queue.Count;MaximumQueued=Math.Max(MaximumQueued,count);while(count-->0){Tuple<SendOrPostCallback,object> item;if(queue.TryDequeue(out item))item.Item1(item.Item2);}}
}
static class Program
{
    static int Main(string[] args)
    {
        bool framed=args[1]=="frame";var context=new FrameContext();SynchronizationContext.SetSynchronizationContext(framed?context:null);
        int sent=0,received=0,closed=0,opened=0,maxOutstanding=0,wrongOrder=0;double maximumEchoSeconds=0;var sentAt=new double[3000];string closeType="";
        var watch=Stopwatch.StartNew();var transport=new BrowserSocketTransport();transport.Opened+=()=>opened++;
        transport.Message+=text=>{int id;if(!text.StartsWith("p")||!int.TryParse(text.Substring(1,8),out id)||id<0||id>=sentAt.Length){wrongOrder++;return;}if(id!=received)wrongOrder++;received++;maximumEchoSeconds=Math.Max(maximumEchoSeconds,watch.Elapsed.TotalSeconds-sentAt[id]);};
        transport.Closed+=reason=>{closed++;closeType=reason=="closed"?"closed":reason=="send failed"?"send_failed":reason=="WebSocketException"?"WebSocketException":"other";};
        transport.Connect(args[0]);double start=-1,nextSend=0;
        while(watch.Elapsed.TotalSeconds<25)
        {
            double now=watch.Elapsed.TotalSeconds;context.Frame();transport.Poll();
            if(opened>0&&start<0){start=now;nextSend=now;}
            if(start>=0&&now-start<20){int steps=0;while(now>=nextSend&&steps++<4){sentAt[sent]=watch.Elapsed.TotalSeconds;transport.Send("p"+sent.ToString("D8",CultureInfo.InvariantCulture)+"_"+new string('x',190));sent++;nextSend+=1d/60;}}
            maxOutstanding=Math.Max(maxOutstanding,sent-received);if(start>=0&&now-start>=20&&sent==received)break;Thread.Sleep(16);
        }
        transport.Dispose();SynchronizationContext.SetSynchronizationContext(null);
        string report="{\"mode\":\""+args[1]+"\",\"mono\":"+(Type.GetType("Mono.Runtime")!=null?"true":"false")+",\"sent\":"+sent+",\"received\":"+received+",\"opened\":"+opened+",\"closed\":"+closed+",\"wrongOrder\":"+wrongOrder+",\"maximumOutstanding\":"+maxOutstanding+",\"maximumEchoSeconds\":"+maximumEchoSeconds.ToString("R",CultureInfo.InvariantCulture)+",\"contextPosts\":"+context.Posts+",\"maximumContextQueued\":"+context.MaximumQueued+",\"closeType\":\""+closeType+"\"}";
        File.WriteAllText(args[2],report);Console.WriteLine(report);return sent==received&&wrongOrder==0&&closed==0?0:1;
    }
}
