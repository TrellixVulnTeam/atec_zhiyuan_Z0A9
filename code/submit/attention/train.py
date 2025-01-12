# coding = utf-8
import os
import sys
import torch
import torch.autograd as autograd
import torch.nn.functional as F
import torch.nn as nn
import pandas as pd
import traceback
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score

def train(train_iter, dev_iter, model, args):
    if args.cuda:
        model.cuda()
    parameters = list(filter(lambda p: p.requires_grad, model.parameters()))
    optimizer = torch.optim.Adam(parameters, lr=args.lr)
    steps = 0
    best_f1 = 0
    last_step = 0
    
    
    for epoch in range(1, args.epochs+1): 
        print('\nEpoch:%s\n'%epoch)
        model.train()
        for batch in train_iter:
            res_list = []
            label_list = []
            question1, question2, target = batch.question1, batch.question2, batch.label
            if args.cuda:
                question1, question2, target = question1.cuda(), question2.cuda(), target.cuda()
            optimizer.zero_grad()
            logit = model(question1, question2)
            target = target.type(torch.cuda.LongTensor)
            criterion = nn.NLLLoss()
            loss = criterion(logit, target)
            loss.backward()
            optimizer.step()
            
            

            steps += 1
            if steps % args.log_interval == 0:
                corrects = 0 
                length = len(target.data)
                logit = logit.data.max(1)[1].cpu().numpy()
                res_list.extend(logit)
                label_list.extend(target.data.cpu().numpy())
                f1 = f1_score(res_list, label_list)

                # for i in range(length):
                #     a = logit[i].data.max()[0].cpu().numpy()
                #     b = target[i].data
                #     # print a
                #     if a < 0.5 and b == 0:
                #         corrects += 1
                #     elif a >= 0.5 and b == 1:
                #         corrects += 1
                #     else:
                #         pass
                acc = accuracy_score(res_list, label_list)

                sys.stdout.write(
                    '\rBatch[{}] - acc: {:.4f}, - f1: {:.4f}'.format(steps, acc, f1))
            if steps % args.test_interval == 0:
                dev_f1 = eval(dev_iter, model, args)
                if dev_f1 > best_f1:
                    best_f1 = dev_f1
                    last_step = steps
                    if args.save_best:
                        save(model, args.save_dir, 'best', steps, best_f1)
                else:
                    if steps - last_step >= args.early_stop:
                        print('early stop by {} steps.'.format(args.early_stop))



def eval(data_iter, model, args):
    model.eval()
    res_list = []
    label_list = []
    corrects = 0
    for batch in data_iter:
        question1, question2, target = batch.question1, batch.question2, batch.label
        if args.cuda:
            question1, question2, target = question1.cuda(), question2.cuda(), target.cuda()

        logit = model(question1, question2)
        target = target.type(torch.cuda.FloatTensor)
        logit = logit.data.max(1)[1].cpu().numpy()
        res_list.extend(logit)
        label_list.extend(target.data.cpu().numpy())
        
    f1 = f1_score(res_list, label_list)
    #     # target = target.type(torch.FloatTensor)

    #     length = len(target.data)
    #     tp = 0.00000001
    #     fp = 0.00000001
    #     tn = 0.00000001
    #     fn = 0.00000001
    #     threshold = 0.5
    #     for i in range(length):
    #         a = logit[i].data.max()[0].cpu().numpy()
    #         b = target[i].data.cpu().numpy()
    #         # print('%s,   %s' %(str(a), str(b)))
    #         if a < threshold and b == 0:
    #             tn += 1
    #         elif a >= threshold and b == 1:
    #             tp += 1
    #         elif a < threshold and b == 1:
    #             fn += 1
    #         elif a >= threshold and b == 0:
    #             fp += 1
    #     # print tn, tp, fn, fp
    #     precision = float(tp)/float(tp+fp) 
    #     recall = float(tp)/float(tp+fn)
    #     f1 = 2*(precision*recall)/float(precision + recall)        
    # size = float(len(data_iter.dataset))
    # # accuracy = 100.0 * float(corrects)/size
    print('\nEvaluation -  f1: {:.4f} \n'.format(f1))
    return f1


def test(test_iter, model, args):
    threshold = 0.5
    res = []
    for batch in test_iter:
        qid, question1, question2 = batch.id, batch.question1, batch.question2
        # if args.cuda:
        #     qid, question1, question2 = qid.cuda(), question1.cuda(), question2.cuda()
        results = model(question1, question2)
        for i in range(len(qid.data)):
            if results[i].data >= threshold:
                res.append([qid[i].data.cpu().numpy(), '1'])
            #elif results.data[i] < threshold:
            else:
                res.append([qid[i].data.cpu().numpy(), '0'])
    
    # res = sorted(res, key=lambda x: x[0])
    with open(args.res_path, 'w') as f:
        cnt = 1
        for x in res:
            f.write('{}\t{}\n'.format(x[0], x[1]))
            cnt += 1
    
    # with open(args.res_path, 'r') as fin:
    #     for line in fin:
    #         lineno, label = line.strip().split('\t')
    #         lineno = int(lineno)
    

    # res = pd.DataFrame(res, columns=['id', 'label'])
    # res.to_csv(args.res_path, sep='\t', index=False, header=None)


def save(model, save_dir, save_prefix, steps, f1):
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    save_prefix = os.path.join(save_dir, save_prefix)
    save_path = '{}_steps_{}_{}.pt'.format(save_prefix, steps, f1)
    torch.save(model.state_dict(), save_path)

