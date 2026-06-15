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
void err_fun(double *nom_x, double *delta_x, double *out_488496692945809667) {
   out_488496692945809667[0] = delta_x[0] + nom_x[0];
   out_488496692945809667[1] = delta_x[1] + nom_x[1];
   out_488496692945809667[2] = delta_x[2] + nom_x[2];
   out_488496692945809667[3] = delta_x[3] + nom_x[3];
   out_488496692945809667[4] = delta_x[4] + nom_x[4];
   out_488496692945809667[5] = delta_x[5] + nom_x[5];
   out_488496692945809667[6] = delta_x[6] + nom_x[6];
   out_488496692945809667[7] = delta_x[7] + nom_x[7];
   out_488496692945809667[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4539209272711951056) {
   out_4539209272711951056[0] = -nom_x[0] + true_x[0];
   out_4539209272711951056[1] = -nom_x[1] + true_x[1];
   out_4539209272711951056[2] = -nom_x[2] + true_x[2];
   out_4539209272711951056[3] = -nom_x[3] + true_x[3];
   out_4539209272711951056[4] = -nom_x[4] + true_x[4];
   out_4539209272711951056[5] = -nom_x[5] + true_x[5];
   out_4539209272711951056[6] = -nom_x[6] + true_x[6];
   out_4539209272711951056[7] = -nom_x[7] + true_x[7];
   out_4539209272711951056[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8602256134349546689) {
   out_8602256134349546689[0] = 1.0;
   out_8602256134349546689[1] = 0.0;
   out_8602256134349546689[2] = 0.0;
   out_8602256134349546689[3] = 0.0;
   out_8602256134349546689[4] = 0.0;
   out_8602256134349546689[5] = 0.0;
   out_8602256134349546689[6] = 0.0;
   out_8602256134349546689[7] = 0.0;
   out_8602256134349546689[8] = 0.0;
   out_8602256134349546689[9] = 0.0;
   out_8602256134349546689[10] = 1.0;
   out_8602256134349546689[11] = 0.0;
   out_8602256134349546689[12] = 0.0;
   out_8602256134349546689[13] = 0.0;
   out_8602256134349546689[14] = 0.0;
   out_8602256134349546689[15] = 0.0;
   out_8602256134349546689[16] = 0.0;
   out_8602256134349546689[17] = 0.0;
   out_8602256134349546689[18] = 0.0;
   out_8602256134349546689[19] = 0.0;
   out_8602256134349546689[20] = 1.0;
   out_8602256134349546689[21] = 0.0;
   out_8602256134349546689[22] = 0.0;
   out_8602256134349546689[23] = 0.0;
   out_8602256134349546689[24] = 0.0;
   out_8602256134349546689[25] = 0.0;
   out_8602256134349546689[26] = 0.0;
   out_8602256134349546689[27] = 0.0;
   out_8602256134349546689[28] = 0.0;
   out_8602256134349546689[29] = 0.0;
   out_8602256134349546689[30] = 1.0;
   out_8602256134349546689[31] = 0.0;
   out_8602256134349546689[32] = 0.0;
   out_8602256134349546689[33] = 0.0;
   out_8602256134349546689[34] = 0.0;
   out_8602256134349546689[35] = 0.0;
   out_8602256134349546689[36] = 0.0;
   out_8602256134349546689[37] = 0.0;
   out_8602256134349546689[38] = 0.0;
   out_8602256134349546689[39] = 0.0;
   out_8602256134349546689[40] = 1.0;
   out_8602256134349546689[41] = 0.0;
   out_8602256134349546689[42] = 0.0;
   out_8602256134349546689[43] = 0.0;
   out_8602256134349546689[44] = 0.0;
   out_8602256134349546689[45] = 0.0;
   out_8602256134349546689[46] = 0.0;
   out_8602256134349546689[47] = 0.0;
   out_8602256134349546689[48] = 0.0;
   out_8602256134349546689[49] = 0.0;
   out_8602256134349546689[50] = 1.0;
   out_8602256134349546689[51] = 0.0;
   out_8602256134349546689[52] = 0.0;
   out_8602256134349546689[53] = 0.0;
   out_8602256134349546689[54] = 0.0;
   out_8602256134349546689[55] = 0.0;
   out_8602256134349546689[56] = 0.0;
   out_8602256134349546689[57] = 0.0;
   out_8602256134349546689[58] = 0.0;
   out_8602256134349546689[59] = 0.0;
   out_8602256134349546689[60] = 1.0;
   out_8602256134349546689[61] = 0.0;
   out_8602256134349546689[62] = 0.0;
   out_8602256134349546689[63] = 0.0;
   out_8602256134349546689[64] = 0.0;
   out_8602256134349546689[65] = 0.0;
   out_8602256134349546689[66] = 0.0;
   out_8602256134349546689[67] = 0.0;
   out_8602256134349546689[68] = 0.0;
   out_8602256134349546689[69] = 0.0;
   out_8602256134349546689[70] = 1.0;
   out_8602256134349546689[71] = 0.0;
   out_8602256134349546689[72] = 0.0;
   out_8602256134349546689[73] = 0.0;
   out_8602256134349546689[74] = 0.0;
   out_8602256134349546689[75] = 0.0;
   out_8602256134349546689[76] = 0.0;
   out_8602256134349546689[77] = 0.0;
   out_8602256134349546689[78] = 0.0;
   out_8602256134349546689[79] = 0.0;
   out_8602256134349546689[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_5404650696097251297) {
   out_5404650696097251297[0] = state[0];
   out_5404650696097251297[1] = state[1];
   out_5404650696097251297[2] = state[2];
   out_5404650696097251297[3] = state[3];
   out_5404650696097251297[4] = state[4];
   out_5404650696097251297[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_5404650696097251297[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_5404650696097251297[7] = state[7];
   out_5404650696097251297[8] = state[8];
}
void F_fun(double *state, double dt, double *out_3720686995353807718) {
   out_3720686995353807718[0] = 1;
   out_3720686995353807718[1] = 0;
   out_3720686995353807718[2] = 0;
   out_3720686995353807718[3] = 0;
   out_3720686995353807718[4] = 0;
   out_3720686995353807718[5] = 0;
   out_3720686995353807718[6] = 0;
   out_3720686995353807718[7] = 0;
   out_3720686995353807718[8] = 0;
   out_3720686995353807718[9] = 0;
   out_3720686995353807718[10] = 1;
   out_3720686995353807718[11] = 0;
   out_3720686995353807718[12] = 0;
   out_3720686995353807718[13] = 0;
   out_3720686995353807718[14] = 0;
   out_3720686995353807718[15] = 0;
   out_3720686995353807718[16] = 0;
   out_3720686995353807718[17] = 0;
   out_3720686995353807718[18] = 0;
   out_3720686995353807718[19] = 0;
   out_3720686995353807718[20] = 1;
   out_3720686995353807718[21] = 0;
   out_3720686995353807718[22] = 0;
   out_3720686995353807718[23] = 0;
   out_3720686995353807718[24] = 0;
   out_3720686995353807718[25] = 0;
   out_3720686995353807718[26] = 0;
   out_3720686995353807718[27] = 0;
   out_3720686995353807718[28] = 0;
   out_3720686995353807718[29] = 0;
   out_3720686995353807718[30] = 1;
   out_3720686995353807718[31] = 0;
   out_3720686995353807718[32] = 0;
   out_3720686995353807718[33] = 0;
   out_3720686995353807718[34] = 0;
   out_3720686995353807718[35] = 0;
   out_3720686995353807718[36] = 0;
   out_3720686995353807718[37] = 0;
   out_3720686995353807718[38] = 0;
   out_3720686995353807718[39] = 0;
   out_3720686995353807718[40] = 1;
   out_3720686995353807718[41] = 0;
   out_3720686995353807718[42] = 0;
   out_3720686995353807718[43] = 0;
   out_3720686995353807718[44] = 0;
   out_3720686995353807718[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_3720686995353807718[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_3720686995353807718[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3720686995353807718[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_3720686995353807718[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_3720686995353807718[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_3720686995353807718[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_3720686995353807718[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_3720686995353807718[53] = -9.8100000000000005*dt;
   out_3720686995353807718[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_3720686995353807718[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_3720686995353807718[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3720686995353807718[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3720686995353807718[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_3720686995353807718[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_3720686995353807718[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_3720686995353807718[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_3720686995353807718[62] = 0;
   out_3720686995353807718[63] = 0;
   out_3720686995353807718[64] = 0;
   out_3720686995353807718[65] = 0;
   out_3720686995353807718[66] = 0;
   out_3720686995353807718[67] = 0;
   out_3720686995353807718[68] = 0;
   out_3720686995353807718[69] = 0;
   out_3720686995353807718[70] = 1;
   out_3720686995353807718[71] = 0;
   out_3720686995353807718[72] = 0;
   out_3720686995353807718[73] = 0;
   out_3720686995353807718[74] = 0;
   out_3720686995353807718[75] = 0;
   out_3720686995353807718[76] = 0;
   out_3720686995353807718[77] = 0;
   out_3720686995353807718[78] = 0;
   out_3720686995353807718[79] = 0;
   out_3720686995353807718[80] = 1;
}
void h_25(double *state, double *unused, double *out_2947196115150604911) {
   out_2947196115150604911[0] = state[6];
}
void H_25(double *state, double *unused, double *out_5079207495704181541) {
   out_5079207495704181541[0] = 0;
   out_5079207495704181541[1] = 0;
   out_5079207495704181541[2] = 0;
   out_5079207495704181541[3] = 0;
   out_5079207495704181541[4] = 0;
   out_5079207495704181541[5] = 0;
   out_5079207495704181541[6] = 1;
   out_5079207495704181541[7] = 0;
   out_5079207495704181541[8] = 0;
}
void h_24(double *state, double *unused, double *out_5743512623925098853) {
   out_5743512623925098853[0] = state[4];
   out_5743512623925098853[1] = state[5];
}
void H_24(double *state, double *unused, double *out_8637133094506504677) {
   out_8637133094506504677[0] = 0;
   out_8637133094506504677[1] = 0;
   out_8637133094506504677[2] = 0;
   out_8637133094506504677[3] = 0;
   out_8637133094506504677[4] = 1;
   out_8637133094506504677[5] = 0;
   out_8637133094506504677[6] = 0;
   out_8637133094506504677[7] = 0;
   out_8637133094506504677[8] = 0;
   out_8637133094506504677[9] = 0;
   out_8637133094506504677[10] = 0;
   out_8637133094506504677[11] = 0;
   out_8637133094506504677[12] = 0;
   out_8637133094506504677[13] = 0;
   out_8637133094506504677[14] = 1;
   out_8637133094506504677[15] = 0;
   out_8637133094506504677[16] = 0;
   out_8637133094506504677[17] = 0;
}
void h_30(double *state, double *unused, double *out_1496564722521721744) {
   out_1496564722521721744[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6450846236513753320) {
   out_6450846236513753320[0] = 0;
   out_6450846236513753320[1] = 0;
   out_6450846236513753320[2] = 0;
   out_6450846236513753320[3] = 0;
   out_6450846236513753320[4] = 1;
   out_6450846236513753320[5] = 0;
   out_6450846236513753320[6] = 0;
   out_6450846236513753320[7] = 0;
   out_6450846236513753320[8] = 0;
}
void h_26(double *state, double *unused, double *out_7752389444480768998) {
   out_7752389444480768998[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8383733465464982142) {
   out_8383733465464982142[0] = 0;
   out_8383733465464982142[1] = 0;
   out_8383733465464982142[2] = 0;
   out_8383733465464982142[3] = 0;
   out_8383733465464982142[4] = 0;
   out_8383733465464982142[5] = 0;
   out_8383733465464982142[6] = 0;
   out_8383733465464982142[7] = 1;
   out_8383733465464982142[8] = 0;
}
void h_27(double *state, double *unused, double *out_6576952114136391720) {
   out_6576952114136391720[0] = state[3];
}
void H_27(double *state, double *unused, double *out_8625609548314178231) {
   out_8625609548314178231[0] = 0;
   out_8625609548314178231[1] = 0;
   out_8625609548314178231[2] = 0;
   out_8625609548314178231[3] = 1;
   out_8625609548314178231[4] = 0;
   out_8625609548314178231[5] = 0;
   out_8625609548314178231[6] = 0;
   out_8625609548314178231[7] = 0;
   out_8625609548314178231[8] = 0;
}
void h_29(double *state, double *unused, double *out_6498237990182567389) {
   out_6498237990182567389[0] = state[1];
}
void H_29(double *state, double *unused, double *out_5940614892199361136) {
   out_5940614892199361136[0] = 0;
   out_5940614892199361136[1] = 1;
   out_5940614892199361136[2] = 0;
   out_5940614892199361136[3] = 0;
   out_5940614892199361136[4] = 0;
   out_5940614892199361136[5] = 0;
   out_5940614892199361136[6] = 0;
   out_5940614892199361136[7] = 0;
   out_5940614892199361136[8] = 0;
}
void h_28(double *state, double *unused, double *out_6868118691912314251) {
   out_6868118691912314251[0] = state[0];
}
void H_28(double *state, double *unused, double *out_3025372781456291778) {
   out_3025372781456291778[0] = 1;
   out_3025372781456291778[1] = 0;
   out_3025372781456291778[2] = 0;
   out_3025372781456291778[3] = 0;
   out_3025372781456291778[4] = 0;
   out_3025372781456291778[5] = 0;
   out_3025372781456291778[6] = 0;
   out_3025372781456291778[7] = 0;
   out_3025372781456291778[8] = 0;
}
void h_31(double *state, double *unused, double *out_8728712732208595769) {
   out_8728712732208595769[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6290861327493552822) {
   out_6290861327493552822[0] = 0;
   out_6290861327493552822[1] = 0;
   out_6290861327493552822[2] = 0;
   out_6290861327493552822[3] = 0;
   out_6290861327493552822[4] = 0;
   out_6290861327493552822[5] = 0;
   out_6290861327493552822[6] = 0;
   out_6290861327493552822[7] = 0;
   out_6290861327493552822[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_488496692945809667) {
  err_fun(nom_x, delta_x, out_488496692945809667);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4539209272711951056) {
  inv_err_fun(nom_x, true_x, out_4539209272711951056);
}
void car_H_mod_fun(double *state, double *out_8602256134349546689) {
  H_mod_fun(state, out_8602256134349546689);
}
void car_f_fun(double *state, double dt, double *out_5404650696097251297) {
  f_fun(state,  dt, out_5404650696097251297);
}
void car_F_fun(double *state, double dt, double *out_3720686995353807718) {
  F_fun(state,  dt, out_3720686995353807718);
}
void car_h_25(double *state, double *unused, double *out_2947196115150604911) {
  h_25(state, unused, out_2947196115150604911);
}
void car_H_25(double *state, double *unused, double *out_5079207495704181541) {
  H_25(state, unused, out_5079207495704181541);
}
void car_h_24(double *state, double *unused, double *out_5743512623925098853) {
  h_24(state, unused, out_5743512623925098853);
}
void car_H_24(double *state, double *unused, double *out_8637133094506504677) {
  H_24(state, unused, out_8637133094506504677);
}
void car_h_30(double *state, double *unused, double *out_1496564722521721744) {
  h_30(state, unused, out_1496564722521721744);
}
void car_H_30(double *state, double *unused, double *out_6450846236513753320) {
  H_30(state, unused, out_6450846236513753320);
}
void car_h_26(double *state, double *unused, double *out_7752389444480768998) {
  h_26(state, unused, out_7752389444480768998);
}
void car_H_26(double *state, double *unused, double *out_8383733465464982142) {
  H_26(state, unused, out_8383733465464982142);
}
void car_h_27(double *state, double *unused, double *out_6576952114136391720) {
  h_27(state, unused, out_6576952114136391720);
}
void car_H_27(double *state, double *unused, double *out_8625609548314178231) {
  H_27(state, unused, out_8625609548314178231);
}
void car_h_29(double *state, double *unused, double *out_6498237990182567389) {
  h_29(state, unused, out_6498237990182567389);
}
void car_H_29(double *state, double *unused, double *out_5940614892199361136) {
  H_29(state, unused, out_5940614892199361136);
}
void car_h_28(double *state, double *unused, double *out_6868118691912314251) {
  h_28(state, unused, out_6868118691912314251);
}
void car_H_28(double *state, double *unused, double *out_3025372781456291778) {
  H_28(state, unused, out_3025372781456291778);
}
void car_h_31(double *state, double *unused, double *out_8728712732208595769) {
  h_31(state, unused, out_8728712732208595769);
}
void car_H_31(double *state, double *unused, double *out_6290861327493552822) {
  H_31(state, unused, out_6290861327493552822);
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
