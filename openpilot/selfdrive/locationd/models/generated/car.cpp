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
void err_fun(double *nom_x, double *delta_x, double *out_5032200201446894984) {
   out_5032200201446894984[0] = delta_x[0] + nom_x[0];
   out_5032200201446894984[1] = delta_x[1] + nom_x[1];
   out_5032200201446894984[2] = delta_x[2] + nom_x[2];
   out_5032200201446894984[3] = delta_x[3] + nom_x[3];
   out_5032200201446894984[4] = delta_x[4] + nom_x[4];
   out_5032200201446894984[5] = delta_x[5] + nom_x[5];
   out_5032200201446894984[6] = delta_x[6] + nom_x[6];
   out_5032200201446894984[7] = delta_x[7] + nom_x[7];
   out_5032200201446894984[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_7143447445886649280) {
   out_7143447445886649280[0] = -nom_x[0] + true_x[0];
   out_7143447445886649280[1] = -nom_x[1] + true_x[1];
   out_7143447445886649280[2] = -nom_x[2] + true_x[2];
   out_7143447445886649280[3] = -nom_x[3] + true_x[3];
   out_7143447445886649280[4] = -nom_x[4] + true_x[4];
   out_7143447445886649280[5] = -nom_x[5] + true_x[5];
   out_7143447445886649280[6] = -nom_x[6] + true_x[6];
   out_7143447445886649280[7] = -nom_x[7] + true_x[7];
   out_7143447445886649280[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_1685754253580569061) {
   out_1685754253580569061[0] = 1.0;
   out_1685754253580569061[1] = 0.0;
   out_1685754253580569061[2] = 0.0;
   out_1685754253580569061[3] = 0.0;
   out_1685754253580569061[4] = 0.0;
   out_1685754253580569061[5] = 0.0;
   out_1685754253580569061[6] = 0.0;
   out_1685754253580569061[7] = 0.0;
   out_1685754253580569061[8] = 0.0;
   out_1685754253580569061[9] = 0.0;
   out_1685754253580569061[10] = 1.0;
   out_1685754253580569061[11] = 0.0;
   out_1685754253580569061[12] = 0.0;
   out_1685754253580569061[13] = 0.0;
   out_1685754253580569061[14] = 0.0;
   out_1685754253580569061[15] = 0.0;
   out_1685754253580569061[16] = 0.0;
   out_1685754253580569061[17] = 0.0;
   out_1685754253580569061[18] = 0.0;
   out_1685754253580569061[19] = 0.0;
   out_1685754253580569061[20] = 1.0;
   out_1685754253580569061[21] = 0.0;
   out_1685754253580569061[22] = 0.0;
   out_1685754253580569061[23] = 0.0;
   out_1685754253580569061[24] = 0.0;
   out_1685754253580569061[25] = 0.0;
   out_1685754253580569061[26] = 0.0;
   out_1685754253580569061[27] = 0.0;
   out_1685754253580569061[28] = 0.0;
   out_1685754253580569061[29] = 0.0;
   out_1685754253580569061[30] = 1.0;
   out_1685754253580569061[31] = 0.0;
   out_1685754253580569061[32] = 0.0;
   out_1685754253580569061[33] = 0.0;
   out_1685754253580569061[34] = 0.0;
   out_1685754253580569061[35] = 0.0;
   out_1685754253580569061[36] = 0.0;
   out_1685754253580569061[37] = 0.0;
   out_1685754253580569061[38] = 0.0;
   out_1685754253580569061[39] = 0.0;
   out_1685754253580569061[40] = 1.0;
   out_1685754253580569061[41] = 0.0;
   out_1685754253580569061[42] = 0.0;
   out_1685754253580569061[43] = 0.0;
   out_1685754253580569061[44] = 0.0;
   out_1685754253580569061[45] = 0.0;
   out_1685754253580569061[46] = 0.0;
   out_1685754253580569061[47] = 0.0;
   out_1685754253580569061[48] = 0.0;
   out_1685754253580569061[49] = 0.0;
   out_1685754253580569061[50] = 1.0;
   out_1685754253580569061[51] = 0.0;
   out_1685754253580569061[52] = 0.0;
   out_1685754253580569061[53] = 0.0;
   out_1685754253580569061[54] = 0.0;
   out_1685754253580569061[55] = 0.0;
   out_1685754253580569061[56] = 0.0;
   out_1685754253580569061[57] = 0.0;
   out_1685754253580569061[58] = 0.0;
   out_1685754253580569061[59] = 0.0;
   out_1685754253580569061[60] = 1.0;
   out_1685754253580569061[61] = 0.0;
   out_1685754253580569061[62] = 0.0;
   out_1685754253580569061[63] = 0.0;
   out_1685754253580569061[64] = 0.0;
   out_1685754253580569061[65] = 0.0;
   out_1685754253580569061[66] = 0.0;
   out_1685754253580569061[67] = 0.0;
   out_1685754253580569061[68] = 0.0;
   out_1685754253580569061[69] = 0.0;
   out_1685754253580569061[70] = 1.0;
   out_1685754253580569061[71] = 0.0;
   out_1685754253580569061[72] = 0.0;
   out_1685754253580569061[73] = 0.0;
   out_1685754253580569061[74] = 0.0;
   out_1685754253580569061[75] = 0.0;
   out_1685754253580569061[76] = 0.0;
   out_1685754253580569061[77] = 0.0;
   out_1685754253580569061[78] = 0.0;
   out_1685754253580569061[79] = 0.0;
   out_1685754253580569061[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_8909179533363476452) {
   out_8909179533363476452[0] = state[0];
   out_8909179533363476452[1] = state[1];
   out_8909179533363476452[2] = state[2];
   out_8909179533363476452[3] = state[3];
   out_8909179533363476452[4] = state[4];
   out_8909179533363476452[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_8909179533363476452[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_8909179533363476452[7] = state[7];
   out_8909179533363476452[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3419672683889849262) {
   out_3419672683889849262[0] = 1;
   out_3419672683889849262[1] = 0;
   out_3419672683889849262[2] = 0;
   out_3419672683889849262[3] = 0;
   out_3419672683889849262[4] = 0;
   out_3419672683889849262[5] = 0;
   out_3419672683889849262[6] = 0;
   out_3419672683889849262[7] = 0;
   out_3419672683889849262[8] = 0;
   out_3419672683889849262[9] = 0;
   out_3419672683889849262[10] = 1;
   out_3419672683889849262[11] = 0;
   out_3419672683889849262[12] = 0;
   out_3419672683889849262[13] = 0;
   out_3419672683889849262[14] = 0;
   out_3419672683889849262[15] = 0;
   out_3419672683889849262[16] = 0;
   out_3419672683889849262[17] = 0;
   out_3419672683889849262[18] = 0;
   out_3419672683889849262[19] = 0;
   out_3419672683889849262[20] = 1;
   out_3419672683889849262[21] = 0;
   out_3419672683889849262[22] = 0;
   out_3419672683889849262[23] = 0;
   out_3419672683889849262[24] = 0;
   out_3419672683889849262[25] = 0;
   out_3419672683889849262[26] = 0;
   out_3419672683889849262[27] = 0;
   out_3419672683889849262[28] = 0;
   out_3419672683889849262[29] = 0;
   out_3419672683889849262[30] = 1;
   out_3419672683889849262[31] = 0;
   out_3419672683889849262[32] = 0;
   out_3419672683889849262[33] = 0;
   out_3419672683889849262[34] = 0;
   out_3419672683889849262[35] = 0;
   out_3419672683889849262[36] = 0;
   out_3419672683889849262[37] = 0;
   out_3419672683889849262[38] = 0;
   out_3419672683889849262[39] = 0;
   out_3419672683889849262[40] = 1;
   out_3419672683889849262[41] = 0;
   out_3419672683889849262[42] = 0;
   out_3419672683889849262[43] = 0;
   out_3419672683889849262[44] = 0;
   out_3419672683889849262[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3419672683889849262[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3419672683889849262[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3419672683889849262[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3419672683889849262[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3419672683889849262[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3419672683889849262[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3419672683889849262[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3419672683889849262[53] = -9.8100000000000005*dt;
   out_3419672683889849262[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3419672683889849262[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3419672683889849262[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3419672683889849262[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3419672683889849262[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3419672683889849262[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3419672683889849262[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3419672683889849262[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3419672683889849262[62] = 0;
   out_3419672683889849262[63] = 0;
   out_3419672683889849262[64] = 0;
   out_3419672683889849262[65] = 0;
   out_3419672683889849262[66] = 0;
   out_3419672683889849262[67] = 0;
   out_3419672683889849262[68] = 0;
   out_3419672683889849262[69] = 0;
   out_3419672683889849262[70] = 1;
   out_3419672683889849262[71] = 0;
   out_3419672683889849262[72] = 0;
   out_3419672683889849262[73] = 0;
   out_3419672683889849262[74] = 0;
   out_3419672683889849262[75] = 0;
   out_3419672683889849262[76] = 0;
   out_3419672683889849262[77] = 0;
   out_3419672683889849262[78] = 0;
   out_3419672683889849262[79] = 0;
   out_3419672683889849262[80] = 1;
}
void h_25(double *state, double *unused, double *out_5555793351249648290) {
   out_5555793351249648290[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4322311178595995255) {
   out_4322311178595995255[0] = 0;
   out_4322311178595995255[1] = 0;
   out_4322311178595995255[2] = 0;
   out_4322311178595995255[3] = 0;
   out_4322311178595995255[4] = 0;
   out_4322311178595995255[5] = 0;
   out_4322311178595995255[6] = 1;
   out_4322311178595995255[7] = 0;
   out_4322311178595995255[8] = 0;
}
void h_24(double *state, double *unused, double *out_8637534363345985562) {
   out_8637534363345985562[0] = state[4];
   out_8637534363345985562[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2909282930557586418) {
   out_2909282930557586418[0] = 0;
   out_2909282930557586418[1] = 0;
   out_2909282930557586418[2] = 0;
   out_2909282930557586418[3] = 0;
   out_2909282930557586418[4] = 1;
   out_2909282930557586418[5] = 0;
   out_2909282930557586418[6] = 0;
   out_2909282930557586418[7] = 0;
   out_2909282930557586418[8] = 0;
   out_2909282930557586418[9] = 0;
   out_2909282930557586418[10] = 0;
   out_2909282930557586418[11] = 0;
   out_2909282930557586418[12] = 0;
   out_2909282930557586418[13] = 0;
   out_2909282930557586418[14] = 1;
   out_2909282930557586418[15] = 0;
   out_2909282930557586418[16] = 0;
   out_2909282930557586418[17] = 0;
}
void h_30(double *state, double *unused, double *out_5127685465639230885) {
   out_5127685465639230885[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8850007508723603453) {
   out_8850007508723603453[0] = 0;
   out_8850007508723603453[1] = 0;
   out_8850007508723603453[2] = 0;
   out_8850007508723603453[3] = 0;
   out_8850007508723603453[4] = 1;
   out_8850007508723603453[5] = 0;
   out_8850007508723603453[6] = 0;
   out_8850007508723603453[7] = 0;
   out_8850007508723603453[8] = 0;
}
void h_26(double *state, double *unused, double *out_4524369580962753368) {
   out_4524369580962753368[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8063814497470051479) {
   out_8063814497470051479[0] = 0;
   out_8063814497470051479[1] = 0;
   out_8063814497470051479[2] = 0;
   out_8063814497470051479[3] = 0;
   out_8063814497470051479[4] = 0;
   out_8063814497470051479[5] = 0;
   out_8063814497470051479[6] = 0;
   out_8063814497470051479[7] = 1;
   out_8063814497470051479[8] = 0;
}
void h_27(double *state, double *unused, double *out_3908981550453062561) {
   out_3908981550453062561[0] = state[3];
}
void H_27(double *state, double *unused, double *out_7421973253185523252) {
   out_7421973253185523252[0] = 0;
   out_7421973253185523252[1] = 0;
   out_7421973253185523252[2] = 0;
   out_7421973253185523252[3] = 1;
   out_7421973253185523252[4] = 0;
   out_7421973253185523252[5] = 0;
   out_7421973253185523252[6] = 0;
   out_7421973253185523252[7] = 0;
   out_7421973253185523252[8] = 0;
}
void h_29(double *state, double *unused, double *out_3307563392839699007) {
   out_3307563392839699007[0] = state[1];
}
void H_29(double *state, double *unused, double *out_8339776164409211269) {
   out_8339776164409211269[0] = 0;
   out_8339776164409211269[1] = 1;
   out_8339776164409211269[2] = 0;
   out_8339776164409211269[3] = 0;
   out_8339776164409211269[4] = 0;
   out_8339776164409211269[5] = 0;
   out_8339776164409211269[6] = 0;
   out_8339776164409211269[7] = 0;
   out_8339776164409211269[8] = 0;
}
void h_28(double *state, double *unused, double *out_8910654818113908206) {
   out_8910654818113908206[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6376145892843885018) {
   out_6376145892843885018[0] = 1;
   out_6376145892843885018[1] = 0;
   out_6376145892843885018[2] = 0;
   out_6376145892843885018[3] = 0;
   out_6376145892843885018[4] = 0;
   out_6376145892843885018[5] = 0;
   out_6376145892843885018[6] = 0;
   out_6376145892843885018[7] = 0;
   out_6376145892843885018[8] = 0;
}
void h_31(double *state, double *unused, double *out_357939675421100083) {
   out_357939675421100083[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8690022599703402955) {
   out_8690022599703402955[0] = 0;
   out_8690022599703402955[1] = 0;
   out_8690022599703402955[2] = 0;
   out_8690022599703402955[3] = 0;
   out_8690022599703402955[4] = 0;
   out_8690022599703402955[5] = 0;
   out_8690022599703402955[6] = 0;
   out_8690022599703402955[7] = 0;
   out_8690022599703402955[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_5032200201446894984) {
  err_fun(nom_x, delta_x, out_5032200201446894984);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7143447445886649280) {
  inv_err_fun(nom_x, true_x, out_7143447445886649280);
}
void car_H_mod_fun(double *state, double *out_1685754253580569061) {
  H_mod_fun(state, out_1685754253580569061);
}
void car_f_fun(double *state, double dt, double *out_8909179533363476452) {
  f_fun(state,  dt, out_8909179533363476452);
}
void car_F_fun(double *state, double dt, double *out_3419672683889849262) {
  F_fun(state,  dt, out_3419672683889849262);
}
void car_h_25(double *state, double *unused, double *out_5555793351249648290) {
  h_25(state, unused, out_5555793351249648290);
}
void car_H_25(double *state, double *unused, double *out_4322311178595995255) {
  H_25(state, unused, out_4322311178595995255);
}
void car_h_24(double *state, double *unused, double *out_8637534363345985562) {
  h_24(state, unused, out_8637534363345985562);
}
void car_H_24(double *state, double *unused, double *out_2909282930557586418) {
  H_24(state, unused, out_2909282930557586418);
}
void car_h_30(double *state, double *unused, double *out_5127685465639230885) {
  h_30(state, unused, out_5127685465639230885);
}
void car_H_30(double *state, double *unused, double *out_8850007508723603453) {
  H_30(state, unused, out_8850007508723603453);
}
void car_h_26(double *state, double *unused, double *out_4524369580962753368) {
  h_26(state, unused, out_4524369580962753368);
}
void car_H_26(double *state, double *unused, double *out_8063814497470051479) {
  H_26(state, unused, out_8063814497470051479);
}
void car_h_27(double *state, double *unused, double *out_3908981550453062561) {
  h_27(state, unused, out_3908981550453062561);
}
void car_H_27(double *state, double *unused, double *out_7421973253185523252) {
  H_27(state, unused, out_7421973253185523252);
}
void car_h_29(double *state, double *unused, double *out_3307563392839699007) {
  h_29(state, unused, out_3307563392839699007);
}
void car_H_29(double *state, double *unused, double *out_8339776164409211269) {
  H_29(state, unused, out_8339776164409211269);
}
void car_h_28(double *state, double *unused, double *out_8910654818113908206) {
  h_28(state, unused, out_8910654818113908206);
}
void car_H_28(double *state, double *unused, double *out_6376145892843885018) {
  H_28(state, unused, out_6376145892843885018);
}
void car_h_31(double *state, double *unused, double *out_357939675421100083) {
  h_31(state, unused, out_357939675421100083);
}
void car_H_31(double *state, double *unused, double *out_8690022599703402955) {
  H_31(state, unused, out_8690022599703402955);
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
