#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_4276335218073679407) {
   out_4276335218073679407[0] = delta_x[0] + nom_x[0];
   out_4276335218073679407[1] = delta_x[1] + nom_x[1];
   out_4276335218073679407[2] = delta_x[2] + nom_x[2];
   out_4276335218073679407[3] = delta_x[3] + nom_x[3];
   out_4276335218073679407[4] = delta_x[4] + nom_x[4];
   out_4276335218073679407[5] = delta_x[5] + nom_x[5];
   out_4276335218073679407[6] = delta_x[6] + nom_x[6];
   out_4276335218073679407[7] = delta_x[7] + nom_x[7];
   out_4276335218073679407[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3738278089596769997) {
   out_3738278089596769997[0] = -nom_x[0] + true_x[0];
   out_3738278089596769997[1] = -nom_x[1] + true_x[1];
   out_3738278089596769997[2] = -nom_x[2] + true_x[2];
   out_3738278089596769997[3] = -nom_x[3] + true_x[3];
   out_3738278089596769997[4] = -nom_x[4] + true_x[4];
   out_3738278089596769997[5] = -nom_x[5] + true_x[5];
   out_3738278089596769997[6] = -nom_x[6] + true_x[6];
   out_3738278089596769997[7] = -nom_x[7] + true_x[7];
   out_3738278089596769997[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8858046684809825962) {
   out_8858046684809825962[0] = 1.0;
   out_8858046684809825962[1] = 0.0;
   out_8858046684809825962[2] = 0.0;
   out_8858046684809825962[3] = 0.0;
   out_8858046684809825962[4] = 0.0;
   out_8858046684809825962[5] = 0.0;
   out_8858046684809825962[6] = 0.0;
   out_8858046684809825962[7] = 0.0;
   out_8858046684809825962[8] = 0.0;
   out_8858046684809825962[9] = 0.0;
   out_8858046684809825962[10] = 1.0;
   out_8858046684809825962[11] = 0.0;
   out_8858046684809825962[12] = 0.0;
   out_8858046684809825962[13] = 0.0;
   out_8858046684809825962[14] = 0.0;
   out_8858046684809825962[15] = 0.0;
   out_8858046684809825962[16] = 0.0;
   out_8858046684809825962[17] = 0.0;
   out_8858046684809825962[18] = 0.0;
   out_8858046684809825962[19] = 0.0;
   out_8858046684809825962[20] = 1.0;
   out_8858046684809825962[21] = 0.0;
   out_8858046684809825962[22] = 0.0;
   out_8858046684809825962[23] = 0.0;
   out_8858046684809825962[24] = 0.0;
   out_8858046684809825962[25] = 0.0;
   out_8858046684809825962[26] = 0.0;
   out_8858046684809825962[27] = 0.0;
   out_8858046684809825962[28] = 0.0;
   out_8858046684809825962[29] = 0.0;
   out_8858046684809825962[30] = 1.0;
   out_8858046684809825962[31] = 0.0;
   out_8858046684809825962[32] = 0.0;
   out_8858046684809825962[33] = 0.0;
   out_8858046684809825962[34] = 0.0;
   out_8858046684809825962[35] = 0.0;
   out_8858046684809825962[36] = 0.0;
   out_8858046684809825962[37] = 0.0;
   out_8858046684809825962[38] = 0.0;
   out_8858046684809825962[39] = 0.0;
   out_8858046684809825962[40] = 1.0;
   out_8858046684809825962[41] = 0.0;
   out_8858046684809825962[42] = 0.0;
   out_8858046684809825962[43] = 0.0;
   out_8858046684809825962[44] = 0.0;
   out_8858046684809825962[45] = 0.0;
   out_8858046684809825962[46] = 0.0;
   out_8858046684809825962[47] = 0.0;
   out_8858046684809825962[48] = 0.0;
   out_8858046684809825962[49] = 0.0;
   out_8858046684809825962[50] = 1.0;
   out_8858046684809825962[51] = 0.0;
   out_8858046684809825962[52] = 0.0;
   out_8858046684809825962[53] = 0.0;
   out_8858046684809825962[54] = 0.0;
   out_8858046684809825962[55] = 0.0;
   out_8858046684809825962[56] = 0.0;
   out_8858046684809825962[57] = 0.0;
   out_8858046684809825962[58] = 0.0;
   out_8858046684809825962[59] = 0.0;
   out_8858046684809825962[60] = 1.0;
   out_8858046684809825962[61] = 0.0;
   out_8858046684809825962[62] = 0.0;
   out_8858046684809825962[63] = 0.0;
   out_8858046684809825962[64] = 0.0;
   out_8858046684809825962[65] = 0.0;
   out_8858046684809825962[66] = 0.0;
   out_8858046684809825962[67] = 0.0;
   out_8858046684809825962[68] = 0.0;
   out_8858046684809825962[69] = 0.0;
   out_8858046684809825962[70] = 1.0;
   out_8858046684809825962[71] = 0.0;
   out_8858046684809825962[72] = 0.0;
   out_8858046684809825962[73] = 0.0;
   out_8858046684809825962[74] = 0.0;
   out_8858046684809825962[75] = 0.0;
   out_8858046684809825962[76] = 0.0;
   out_8858046684809825962[77] = 0.0;
   out_8858046684809825962[78] = 0.0;
   out_8858046684809825962[79] = 0.0;
   out_8858046684809825962[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2600173016712354575) {
   out_2600173016712354575[0] = state[0];
   out_2600173016712354575[1] = state[1];
   out_2600173016712354575[2] = state[2];
   out_2600173016712354575[3] = state[3];
   out_2600173016712354575[4] = state[4];
   out_2600173016712354575[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2600173016712354575[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2600173016712354575[7] = state[7];
   out_2600173016712354575[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2418560584693982231) {
   out_2418560584693982231[0] = 1;
   out_2418560584693982231[1] = 0;
   out_2418560584693982231[2] = 0;
   out_2418560584693982231[3] = 0;
   out_2418560584693982231[4] = 0;
   out_2418560584693982231[5] = 0;
   out_2418560584693982231[6] = 0;
   out_2418560584693982231[7] = 0;
   out_2418560584693982231[8] = 0;
   out_2418560584693982231[9] = 0;
   out_2418560584693982231[10] = 1;
   out_2418560584693982231[11] = 0;
   out_2418560584693982231[12] = 0;
   out_2418560584693982231[13] = 0;
   out_2418560584693982231[14] = 0;
   out_2418560584693982231[15] = 0;
   out_2418560584693982231[16] = 0;
   out_2418560584693982231[17] = 0;
   out_2418560584693982231[18] = 0;
   out_2418560584693982231[19] = 0;
   out_2418560584693982231[20] = 1;
   out_2418560584693982231[21] = 0;
   out_2418560584693982231[22] = 0;
   out_2418560584693982231[23] = 0;
   out_2418560584693982231[24] = 0;
   out_2418560584693982231[25] = 0;
   out_2418560584693982231[26] = 0;
   out_2418560584693982231[27] = 0;
   out_2418560584693982231[28] = 0;
   out_2418560584693982231[29] = 0;
   out_2418560584693982231[30] = 1;
   out_2418560584693982231[31] = 0;
   out_2418560584693982231[32] = 0;
   out_2418560584693982231[33] = 0;
   out_2418560584693982231[34] = 0;
   out_2418560584693982231[35] = 0;
   out_2418560584693982231[36] = 0;
   out_2418560584693982231[37] = 0;
   out_2418560584693982231[38] = 0;
   out_2418560584693982231[39] = 0;
   out_2418560584693982231[40] = 1;
   out_2418560584693982231[41] = 0;
   out_2418560584693982231[42] = 0;
   out_2418560584693982231[43] = 0;
   out_2418560584693982231[44] = 0;
   out_2418560584693982231[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2418560584693982231[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2418560584693982231[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2418560584693982231[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2418560584693982231[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2418560584693982231[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2418560584693982231[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2418560584693982231[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2418560584693982231[53] = -9.8100000000000005*dt;
   out_2418560584693982231[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2418560584693982231[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2418560584693982231[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2418560584693982231[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2418560584693982231[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2418560584693982231[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2418560584693982231[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2418560584693982231[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2418560584693982231[62] = 0;
   out_2418560584693982231[63] = 0;
   out_2418560584693982231[64] = 0;
   out_2418560584693982231[65] = 0;
   out_2418560584693982231[66] = 0;
   out_2418560584693982231[67] = 0;
   out_2418560584693982231[68] = 0;
   out_2418560584693982231[69] = 0;
   out_2418560584693982231[70] = 1;
   out_2418560584693982231[71] = 0;
   out_2418560584693982231[72] = 0;
   out_2418560584693982231[73] = 0;
   out_2418560584693982231[74] = 0;
   out_2418560584693982231[75] = 0;
   out_2418560584693982231[76] = 0;
   out_2418560584693982231[77] = 0;
   out_2418560584693982231[78] = 0;
   out_2418560584693982231[79] = 0;
   out_2418560584693982231[80] = 1;
}
void h_25(double *state, double *unused, double *out_7368322694207597671) {
   out_7368322694207597671[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2361023724919796011) {
   out_2361023724919796011[0] = 0;
   out_2361023724919796011[1] = 0;
   out_2361023724919796011[2] = 0;
   out_2361023724919796011[3] = 0;
   out_2361023724919796011[4] = 0;
   out_2361023724919796011[5] = 0;
   out_2361023724919796011[6] = 1;
   out_2361023724919796011[7] = 0;
   out_2361023724919796011[8] = 0;
}
void h_24(double *state, double *unused, double *out_3157655832268166165) {
   out_3157655832268166165[0] = state[4];
   out_3157655832268166165[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1890566242876457287) {
   out_1890566242876457287[0] = 0;
   out_1890566242876457287[1] = 0;
   out_1890566242876457287[2] = 0;
   out_1890566242876457287[3] = 0;
   out_1890566242876457287[4] = 1;
   out_1890566242876457287[5] = 0;
   out_1890566242876457287[6] = 0;
   out_1890566242876457287[7] = 0;
   out_1890566242876457287[8] = 0;
   out_1890566242876457287[9] = 0;
   out_1890566242876457287[10] = 0;
   out_1890566242876457287[11] = 0;
   out_1890566242876457287[12] = 0;
   out_1890566242876457287[13] = 0;
   out_1890566242876457287[14] = 1;
   out_1890566242876457287[15] = 0;
   out_1890566242876457287[16] = 0;
   out_1890566242876457287[17] = 0;
}
void h_30(double *state, double *unused, double *out_3617862615253065620) {
   out_3617862615253065620[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2166672605207812187) {
   out_2166672605207812187[0] = 0;
   out_2166672605207812187[1] = 0;
   out_2166672605207812187[2] = 0;
   out_2166672605207812187[3] = 0;
   out_2166672605207812187[4] = 1;
   out_2166672605207812187[5] = 0;
   out_2166672605207812187[6] = 0;
   out_2166672605207812187[7] = 0;
   out_2166672605207812187[8] = 0;
}
void h_26(double *state, double *unused, double *out_5806150257954055878) {
   out_5806150257954055878[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1380479593954260213) {
   out_1380479593954260213[0] = 0;
   out_1380479593954260213[1] = 0;
   out_1380479593954260213[2] = 0;
   out_1380479593954260213[3] = 0;
   out_1380479593954260213[4] = 0;
   out_1380479593954260213[5] = 0;
   out_1380479593954260213[6] = 0;
   out_1380479593954260213[7] = 1;
   out_1380479593954260213[8] = 0;
}
void h_27(double *state, double *unused, double *out_8727950225216967499) {
   out_8727950225216967499[0] = state[3];
}
void H_27(double *state, double *unused, double *out_56921465976131030) {
   out_56921465976131030[0] = 0;
   out_56921465976131030[1] = 0;
   out_56921465976131030[2] = 0;
   out_56921465976131030[3] = 1;
   out_56921465976131030[4] = 0;
   out_56921465976131030[5] = 0;
   out_56921465976131030[6] = 0;
   out_56921465976131030[7] = 0;
   out_56921465976131030[8] = 0;
}
void h_29(double *state, double *unused, double *out_2947958622142233181) {
   out_2947958622142233181[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1656441260893420003) {
   out_1656441260893420003[0] = 0;
   out_1656441260893420003[1] = 1;
   out_1656441260893420003[2] = 0;
   out_1656441260893420003[3] = 0;
   out_1656441260893420003[4] = 0;
   out_1656441260893420003[5] = 0;
   out_1656441260893420003[6] = 0;
   out_1656441260893420003[7] = 0;
   out_1656441260893420003[8] = 0;
}
void h_28(double *state, double *unused, double *out_8124634340540489982) {
   out_8124634340540489982[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6738840277962950577) {
   out_6738840277962950577[0] = 1;
   out_6738840277962950577[1] = 0;
   out_6738840277962950577[2] = 0;
   out_6738840277962950577[3] = 0;
   out_6738840277962950577[4] = 0;
   out_6738840277962950577[5] = 0;
   out_6738840277962950577[6] = 0;
   out_6738840277962950577[7] = 0;
   out_6738840277962950577[8] = 0;
}
void h_31(double *state, double *unused, double *out_5966358236057140703) {
   out_5966358236057140703[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2391669686796756439) {
   out_2391669686796756439[0] = 0;
   out_2391669686796756439[1] = 0;
   out_2391669686796756439[2] = 0;
   out_2391669686796756439[3] = 0;
   out_2391669686796756439[4] = 0;
   out_2391669686796756439[5] = 0;
   out_2391669686796756439[6] = 0;
   out_2391669686796756439[7] = 0;
   out_2391669686796756439[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_4276335218073679407) {
  err_fun(nom_x, delta_x, out_4276335218073679407);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3738278089596769997) {
  inv_err_fun(nom_x, true_x, out_3738278089596769997);
}
void car_H_mod_fun(double *state, double *out_8858046684809825962) {
  H_mod_fun(state, out_8858046684809825962);
}
void car_f_fun(double *state, double dt, double *out_2600173016712354575) {
  f_fun(state,  dt, out_2600173016712354575);
}
void car_F_fun(double *state, double dt, double *out_2418560584693982231) {
  F_fun(state,  dt, out_2418560584693982231);
}
void car_h_25(double *state, double *unused, double *out_7368322694207597671) {
  h_25(state, unused, out_7368322694207597671);
}
void car_H_25(double *state, double *unused, double *out_2361023724919796011) {
  H_25(state, unused, out_2361023724919796011);
}
void car_h_24(double *state, double *unused, double *out_3157655832268166165) {
  h_24(state, unused, out_3157655832268166165);
}
void car_H_24(double *state, double *unused, double *out_1890566242876457287) {
  H_24(state, unused, out_1890566242876457287);
}
void car_h_30(double *state, double *unused, double *out_3617862615253065620) {
  h_30(state, unused, out_3617862615253065620);
}
void car_H_30(double *state, double *unused, double *out_2166672605207812187) {
  H_30(state, unused, out_2166672605207812187);
}
void car_h_26(double *state, double *unused, double *out_5806150257954055878) {
  h_26(state, unused, out_5806150257954055878);
}
void car_H_26(double *state, double *unused, double *out_1380479593954260213) {
  H_26(state, unused, out_1380479593954260213);
}
void car_h_27(double *state, double *unused, double *out_8727950225216967499) {
  h_27(state, unused, out_8727950225216967499);
}
void car_H_27(double *state, double *unused, double *out_56921465976131030) {
  H_27(state, unused, out_56921465976131030);
}
void car_h_29(double *state, double *unused, double *out_2947958622142233181) {
  h_29(state, unused, out_2947958622142233181);
}
void car_H_29(double *state, double *unused, double *out_1656441260893420003) {
  H_29(state, unused, out_1656441260893420003);
}
void car_h_28(double *state, double *unused, double *out_8124634340540489982) {
  h_28(state, unused, out_8124634340540489982);
}
void car_H_28(double *state, double *unused, double *out_6738840277962950577) {
  H_28(state, unused, out_6738840277962950577);
}
void car_h_31(double *state, double *unused, double *out_5966358236057140703) {
  h_31(state, unused, out_5966358236057140703);
}
void car_H_31(double *state, double *unused, double *out_2391669686796756439) {
  H_31(state, unused, out_2391669686796756439);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
