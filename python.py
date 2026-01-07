from sklearn.neural_network import MLPClassifier
model = MLPClassifier(hidden_layer_sizes=(10,), max_iter=1000).fit([[0,0],[1,1],[0,1]])